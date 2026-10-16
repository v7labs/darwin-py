import json
import uuid

import numpy as np
import pytest
from PIL import Image

from darwin.exporter import get_exporter
from darwin.importer import get_importer
from darwin.lidar import geometry as g
from darwin.lidar.darwin_json import ranges_to_indices, write_darwin_json
from darwin.lidar.nuscenes import (
    build_nuscenes,
    export_nuscenes,
    parse_nuscenes,
    parse_nuscenes_lidarseg,
)
from darwin.lidar.scene import read_scene
from darwin.utils import parse_darwin_json

N_POINTS = 20
K = [[100.0, 0, 80], [0, 100.0, 45], [0, 0, 1]]
CAMS = {  # ego_from_cam rotations: optical axis forward / backward
    "CAM_FRONT": np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0]], float),
    "CAM_BACK": np.array([[0, 0, -1], [1, 0, 0], [0, -1, 0]], float),
}
CATEGORIES = {"noise": 0, "human.pedestrian.adult": 2, "vehicle.car": 17}


def tok():
    return uuid.uuid4().hex


def _pose_rec(pose, **extra):
    return {
        "token": tok(),
        "translation": pose[:3, 3].tolist(),
        "rotation": list(g.rot_to_quat(pose)),
        **extra,
    }


@pytest.fixture
def nusc(tmp_path):
    """A 1-scene, 3-sample v1.0-mini with LIDAR_TOP, two cameras, boxes, lidarseg, panoptic."""
    root = tmp_path / "nuscenes"
    vdir = root / "v1.0-mini"
    vdir.mkdir(parents=True)
    rng = np.random.default_rng(3)
    tables = {
        k: []
        for k in (
            "scene sample sample_data ego_pose calibrated_sensor sensor sample_annotation "
            "instance category attribute lidarseg panoptic log"
        ).split()
    }
    sensors = {}
    for channel in ("LIDAR_TOP", *CAMS):
        rec = {
            "token": tok(),
            "channel": channel,
            "modality": "lidar" if channel == "LIDAR_TOP" else "camera",
        }
        tables["sensor"].append(rec)
        sensors[channel] = rec["token"]
    lidar_pose = g.make_pose(g.euler_to_rot(0, 0, -np.pi / 2), (0.94, 0, 1.84))
    calib = {
        "LIDAR_TOP": _pose_rec(
            lidar_pose, sensor_token=sensors["LIDAR_TOP"], camera_intrinsic=[]
        )
    }
    for cam, r in CAMS.items():
        calib[cam] = _pose_rec(
            g.make_pose(r, (1.7, 0, 1.5)), sensor_token=sensors[cam], camera_intrinsic=K
        )
    tables["calibrated_sensor"] = list(calib.values())
    cats = {
        name: {"token": tok(), "name": name, "index": i}
        for name, i in CATEGORIES.items()
    }
    tables["category"] = list(cats.values())
    attrs = {
        n: {"token": tok(), "name": n}
        for n in ("vehicle.moving", "pedestrian.standing")
    }
    tables["attribute"] = list(attrs.values())
    instances = {
        "car": {"token": tok(), "category_token": cats["vehicle.car"]["token"]},
        "ped": {
            "token": tok(),
            "category_token": cats["human.pedestrian.adult"]["token"],
        },
    }
    tables["instance"] = list(instances.values())
    scene = {"token": tok(), "name": "scene-0061", "log_token": tok()}
    samples = [{"token": tok(), "scene_token": scene["token"]} for _ in range(3)]
    for k, s in enumerate(samples):
        s["timestamp"] = 1_500_000_000_000_000 + k * 500_000
        s["prev"] = samples[k - 1]["token"] if k else ""
        s["next"] = samples[k + 1]["token"] if k < 2 else ""
    scene["first_sample_token"] = samples[0]["token"]
    scene["last_sample_token"] = samples[-1]["token"]
    tables["scene"] = [scene]
    tables["sample"] = samples
    truth = {"points": [], "lidar_ego": [], "cam_ego": [], "labels": [], "panoptic": []}
    for k, s in enumerate(samples):
        for channel in ("LIDAR_TOP", *CAMS):
            dt_us = 0 if channel == "LIDAR_TOP" else 20_000
            ego = g.make_pose(
                g.euler_to_rot(0.01 * k, 0, 0.1 * k + dt_us * 1e-7),
                (100 + 2 * k + dt_us * 1e-5, 200 + k, 0.1),
            )
            ego_rec = _pose_rec(ego, timestamp=s["timestamp"] + dt_us)
            tables["ego_pose"].append(ego_rec)
            if channel == "LIDAR_TOP":
                filename = f"samples/LIDAR_TOP/{k}.pcd.bin"
                pts = rng.uniform(-30, 30, (N_POINTS, 5)).astype("<f4")
                pts[:, 3] = rng.uniform(0, 255, N_POINTS)
                truth["points"].append(pts)
                truth["lidar_ego"].append(ego)
            else:
                filename = f"samples/{channel}/{k}.jpg"
                if channel == "CAM_FRONT":
                    truth["cam_ego"].append(ego)
            path = root / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            if channel == "LIDAR_TOP":
                pts.tofile(path)
            else:
                Image.new("RGB", (160, 90), (k * 40, 10, 10)).save(path)
            sd = {
                "token": tok(),
                "sample_token": s["token"],
                "ego_pose_token": ego_rec["token"],
                "calibrated_sensor_token": calib[channel]["token"],
                "timestamp": s["timestamp"] + dt_us,
                "is_key_frame": True,
                "filename": filename,
            }
            tables["sample_data"].append(sd)
            if channel == "LIDAR_TOP":
                labels = rng.choice([0, 2, 17], N_POINTS).astype(np.uint8)
                inst = np.where(labels == 17, rng.choice([1, 2], N_POINTS), 0)
                inst = np.where(labels == 2, 3, inst)
                pan = (labels.astype(np.uint16) * 1000 + inst).astype(np.uint16)
                truth["labels"].append(labels)
                truth["panoptic"].append(pan)
                for kind, data in (("lidarseg", labels), ("panoptic", pan)):
                    rel = f"{kind}/v1.0-mini/{sd['token']}_{kind}." + (
                        "bin" if kind == "lidarseg" else "npz"
                    )
                    (root / rel).parent.mkdir(parents=True, exist_ok=True)
                    if kind == "lidarseg":
                        data.tofile(root / rel)
                    else:
                        np.savez_compressed(root / rel, data=data)
                    tables[kind].append(
                        {
                            "token": tok(),
                            "sample_data_token": sd["token"],
                            "filename": rel,
                        }
                    )
        # nuScenes ships non-key frames too; they must be ignored
        tables["sample_data"].append(
            {**tables["sample_data"][-1], "token": tok(), "is_key_frame": False}
        )
    anns = []
    for k, s in enumerate(samples):
        car = g.make_pose(
            g.euler_to_rot(0.0, 0.02, 0.5 + 0.1 * k), (110 + 3 * k, 205, 1.0)
        )
        anns.append(("car", s, car, [1.9, 4.6, 1.7], ["vehicle.moving"]))
        if k != 1:
            ped = g.make_pose(g.euler_to_rot(0, 0, -1.0), (105, 198 + k, 0.9))
            anns.append(("ped", s, ped, [0.6, 0.7, 1.8], ["pedestrian.standing"]))
    for name, s, pose, size, attr in anns:
        tables["sample_annotation"].append(
            {
                "token": tok(),
                "sample_token": s["token"],
                "instance_token": instances[name]["token"],
                "translation": pose[:3, 3].tolist(),
                "size": size,
                "rotation": list(g.rot_to_quat(pose)),
                "attribute_tokens": [attrs[a]["token"] for a in attr],
            }
        )
    for name, rows in tables.items():
        (vdir / f"{name}.json").write_text(json.dumps(rows))
    return root, tables, truth


def test_build_points_and_camera_projection(nusc, tmp_path):
    root, tables, truth = nusc
    scene = read_scene(build_nuscenes(root, "scene-0061", tmp_path / "out"))
    assert scene.path.name == "scene-0061.lidar.zip"
    m = scene.manifest
    assert m["fps"] == 2 and m["frame_count"] == 3 and m["coordinate_frame"] == "world"
    assert {c["name"] for c in m["cameras"]} == set(CAMS)
    assert [f["timestamp"] for f in m["frames"]] == pytest.approx([0, 0.5, 1.0])
    origin = truth["lidar_ego"][0][:3, 3]
    lidar = g.make_pose(g.euler_to_rot(0, 0, -np.pi / 2), (0.94, 0, 1.84))
    for k in range(3):
        expected_ego = g.translation(-origin) @ truth["lidar_ego"][k]
        assert np.allclose(scene.ego_pose(k), expected_ego, atol=1e-6)
        expected = g.transform_points(expected_ego @ lidar, truth["points"][k][:, :3])
        assert np.abs(scene.points(k).xyz - expected).max() <= 0.0051
    # a point 10 m in front of CAM_FRONT, 1 m right, 0.5 m down -> pixel (90, 50) at full size
    cam_pose = truth["cam_ego"][1] @ g.make_pose(CAMS["CAM_FRONT"], (1.7, 0, 1.5))
    world = g.transform_points(cam_pose, np.array([[1.0, 0.5, 10.0]]))[0]
    cam = next(c for c in m["cameras"] if c["name"] == "CAM_FRONT")
    mat = np.array(m["frames"][1]["images"]["CAM_FRONT"]["world_to_image"])
    u, v, w = mat @ np.r_[world - origin, 1]
    assert w > 0
    assert np.allclose(
        [u / w, v / w], [90 * cam["width"] / 160, 50 * cam["height"] / 90], atol=1e-3
    )


def test_boxes_round_trip_through_darwin_json(nusc, tmp_path):
    root, tables, truth = nusc
    [af] = parse_nuscenes(root / "v1.0-mini")
    assert af.filename == "scene-0061.lidar.zip"
    assert [a.annotation_class.name for a in af.annotations] == [
        "vehicle.car",
        "human.pedestrian.adult",
    ]
    assert af.annotations[1].segments == [[0, 1], [2, 3]]
    built = read_scene(build_nuscenes(root, "scene-0061", tmp_path / "pkg"))
    meta = af.slots[0].metadata
    for k in range(3):
        assert np.allclose(
            meta["frames"][k]["ego_pose"], built.manifest["frames"][k]["ego_pose"]
        )
    back = parse_darwin_json(write_darwin_json(af, tmp_path / "json"))
    origin = truth["lidar_ego"][0][:3, 3]
    [path] = export_nuscenes([back], tmp_path / "export", origin=origin)
    out = json.loads(path.read_text())
    assert path.name == "scene-0061.json" and out["coordinate_frame"] == "world"
    sample_index = {s["token"]: k for k, s in enumerate(tables["sample"])}
    attr_names = {a["token"]: a["name"] for a in tables["attribute"]}
    cat_of = {
        i["token"]: next(
            c["name"] for c in tables["category"] if c["token"] == i["category_token"]
        )
        for i in tables["instance"]
    }
    exported = {
        (r["instance_token"], f["sample_index"]): r
        for f in out["frames"]
        for r in f["sample_annotation"]
    }
    assert len(exported) == len(tables["sample_annotation"]) == 5
    for a in tables["sample_annotation"]:
        r = exported[(a["instance_token"], sample_index[a["sample_token"]])]
        assert r["translation"] == pytest.approx(a["translation"], abs=1e-6)
        assert r["size"] == pytest.approx(a["size"], abs=1e-6)
        q = np.array(a["rotation"]) * np.sign(a["rotation"][0])
        assert r["rotation"] == pytest.approx(q.tolist(), abs=1e-6)
        assert r["category_name"] == cat_of[a["instance_token"]]
        assert r["attribute_names"] == [attr_names[t] for t in a["attribute_tokens"]]
    for k, f in enumerate(out["frames"]):
        assert f["ego_pose"]["translation"] == pytest.approx(
            truth["lidar_ego"][k][:3, 3], abs=1e-5
        )
    ped = sorted(
        (
            r
            for r in exported.values()
            if r["category_name"] == "human.pedestrian.adult"
        ),
        key=lambda r: r["sample_index"],
    )
    assert ped[0]["next"] == ped[1]["token"] and ped[1]["prev"] == ped[0]["token"]
    assert ped[0]["prev"] == "" and ped[1]["next"] == ""


def _labels_from_masks(af, panoptic):
    index = dict(CATEGORIES)
    frames = {}
    for a in af.annotations:
        for f, frame in a.frames.items():
            sub = frame.get_sub("instance_id")
            value = index[a.annotation_class.name] * (1000 if panoptic else 1)
            value += int(sub.data) if (panoptic and sub) else 0
            data = frame.data
            labels = frames.setdefault(f, np.zeros(data["point_count"], np.int64))
            labels[ranges_to_indices(data["ranges"])] = value
    return frames


@pytest.mark.parametrize("panoptic", [False, True])
def test_lidarseg_and_panoptic_round_trip(nusc, tmp_path, panoptic):
    root, tables, truth = nusc
    [af] = parse_nuscenes_lidarseg(root / "v1.0-mini", panoptic=panoptic)
    back = parse_darwin_json(write_darwin_json(af, tmp_path))
    assert all(
        a.annotation_class.annotation_type == "point_mask_3d" for a in back.annotations
    )
    assert "noise" not in {a.annotation_class.name for a in back.annotations}
    rebuilt = _labels_from_masks(back, panoptic)
    for k in range(3):
        expected = (truth["panoptic"] if panoptic else truth["labels"])[k].astype(
            np.int64
        )
        expected[expected < (1000 if panoptic else 1)] = (
            0  # noise points stay unlabeled
        )
        assert np.array_equal(rebuilt[k], expected)
    if panoptic:
        cars = [a for a in back.annotations if a.annotation_class.name == "vehicle.car"]
        assert len(cars) == 2 and {
            a.frames[0].get_sub("instance_id").data for a in cars if 0 in a.frames
        } <= {1, 2}


def test_registered_formats(nusc, tmp_path):
    root, _, _ = nusc
    vdir = root / "v1.0-mini"
    boxes = get_importer("nuscenes")
    assert boxes(vdir / "scene.json") is None and boxes(vdir) is None
    [af] = boxes(vdir / "sample_annotation.json")
    assert len(af.annotations) == 2
    seg = get_importer("nuscenes_lidarseg")
    assert seg(vdir / "lidarseg.json") is None  # panoptic.json present: it wins
    [pan] = seg(vdir / "panoptic.json")
    assert any(a.frames[min(a.frames)].get_sub("instance_id") for a in pan.annotations)
    (vdir / "panoptic.json").unlink()
    [sem] = seg(vdir / "lidarseg.json")
    assert not any(
        a.frames[min(a.frames)].get_sub("instance_id") for a in sem.annotations
    )
    get_exporter("nuscenes")([af], tmp_path / "out")
    out = json.loads((tmp_path / "out" / "scene-0061.json").read_text())
    assert sum(len(f["sample_annotation"]) for f in out["frames"]) == 5
