import json

import numpy as np
from PIL import Image

from darwin.exporter.formats.semantic_kitti import export
from darwin.importer.formats.semantic_kitti import parse_path
from darwin.lidar import geometry as g
from darwin.lidar.darwin_json import (
    indices_to_ranges,
    mask_to_ranges,
    ranges_to_indices,
    write_darwin_json,
)
from darwin.lidar.scene import read_scene
from darwin.lidar.semantic_kitti import build_kitti_odometry, parse_semantic_kitti
from darwin.utils import parse_darwin_json

RNG = np.random.default_rng(3)
# velo -> cam0: cam x = -velo y, cam y = -velo z, cam z = velo x
TR = np.array([[0, -1, 0, 0.1], [0, 0, -1, -0.08], [1, 0, 0, -0.27]], float)
P2 = np.array([[4.0, 0, 4, 0.5], [0, 4, 4, 0], [0, 0, 1, 0]])


def _sequence(tmp_path, with_poses=True, n=3, points=40):
    seq = tmp_path / "sequences" / "07"
    for d in ("velodyne", "labels", "image_2"):
        (seq / d).mkdir(parents=True)
    labels = []
    for i in range(n):
        pts = RNG.uniform(-10, 10, (points + i, 4)).astype("<f4")
        pts[:, 3] = RNG.uniform(0, 1, len(pts))
        pts.tofile(seq / "velodyne" / f"{i:06d}.bin")
        sem = RNG.choice([0, 1, 10, 40, 252, 300], len(pts)).astype("<u4")
        inst = np.where(np.isin(sem, [10, 252]), RNG.integers(1, 3, len(pts)), 0)
        lab = (sem | (inst.astype("<u4") << 16)).astype("<u4")
        lab.tofile(seq / "labels" / f"{i:06d}.label")
        labels.append(lab)
        Image.fromarray(RNG.integers(0, 255, (8, 8, 3), dtype=np.uint8)).save(
            seq / "image_2" / f"{i:06d}.png"
        )
    (seq / "calib.txt").write_text(
        f"P0: {' '.join(['0'] * 12)}\nP2: {' '.join(map(str, P2.ravel()))}\n"
        f"Tr: {' '.join(map(str, TR.ravel()))}\n"
    )
    (seq / "times.txt").write_text("\n".join(str(5 + i * 0.1) for i in range(n)))
    if with_poses:  # cam0 moves 2 m forward (cam z) per frame and turns a little
        poses = [
            g.make_pose(g.euler_to_rot(0, 0.1 * i, 0), (0, 0, 2.0 * i))[:3]
            for i in range(n)
        ]
        (seq / "poses.txt").write_text(
            "\n".join(" ".join(map(str, p.ravel())) for p in poses)
        )
    return seq, labels


def test_point_mask_ranges():
    assert mask_to_ranges(np.zeros(5, bool)) == []
    assert mask_to_ranges(np.ones(5, bool)) == [0, 5]
    assert mask_to_ranges(np.array([0, 1, 1, 0, 1], bool)) == [1, 2, 4, 1]
    assert indices_to_ranges(np.array([7])) == [7, 1]
    assert ranges_to_indices([1, 2, 4, 1]).tolist() == [1, 2, 4]
    assert ranges_to_indices([]).tolist() == []


def test_build_sensor_frame(tmp_path):
    seq, _ = _sequence(tmp_path, with_poses=False)
    scene = read_scene(build_kitti_odometry(seq, tmp_path / "out", image_scale=0.5))
    assert scene.path.name == "semantickitti_07.lidar.zip"
    m = scene.manifest
    assert m["coordinate_frame"] == "sensor" and len(scene) == 3
    assert [f["timestamp"] for f in m["frames"]] == [0, 0.1, 0.2]
    raw = np.fromfile(seq / "velodyne" / "000001.bin", "<f4").reshape(-1, 4)
    assert np.abs(scene.points(1).xyz - raw[:, :3]).max() <= 0.0051
    expected = np.diag([0.5, 0.5, 1]) @ P2 @ np.vstack([TR, [0, 0, 0, 1]])
    assert np.allclose(m["frames"][0]["images"]["image_2"]["world_to_image"], expected)


def test_build_world_frame(tmp_path):
    seq, _ = _sequence(tmp_path)
    scene = read_scene(build_kitti_odometry(seq, tmp_path, image_scale=1))
    assert scene.manifest["coordinate_frame"] == "world"
    tr = np.vstack([TR, [0, 0, 0, 1]])
    for i in range(3):
        pose_cam = g.make_pose(g.euler_to_rot(0, 0.1 * i, 0), (0, 0, 2.0 * i))
        world_from_velo = g.invert(tr) @ pose_cam @ tr
        assert np.allclose(scene.ego_pose(i), world_from_velo, atol=1e-6)
        raw = np.fromfile(seq / "velodyne" / f"{i:06d}.bin", "<f4").reshape(-1, 4)
        expected = g.transform_points(world_from_velo, raw[:, :3])
        assert np.abs(scene.points(i).xyz - expected).max() <= 0.0051
        # the camera projection of a scene point equals the sensor-frame projection
        m = np.array(scene.frames[i]["images"]["image_2"]["world_to_image"])
        p_scene = np.r_[expected[0], 1]
        assert np.allclose(m @ p_scene, P2 @ tr @ np.r_[raw[0, :3], 1], atol=1e-4)
    # cam0 driving forward (cam z) is the velodyne driving forward (x), give or take the lever arm
    assert abs(scene.ego_pose(1)[0, 3] - 2) < 0.05


def test_labels_round_trip(tmp_path):
    seq, labels = _sequence(tmp_path)
    (af,) = parse_semantic_kitti(seq / "labels")
    assert af.filename == "semantickitti_07.lidar.zip"
    meta = af.slots[0].metadata
    assert meta["coordinate_frame"] == "world" and len(meta["frames"]) == 3
    names = {a.annotation_class.name for a in af.annotations}
    assert names == {"outlier", "car", "road", "moving-car", "class_300"}
    assert all(
        a.annotation_class.annotation_type == "point_mask_3d" for a in af.annotations
    )
    path = write_darwin_json(af, tmp_path / "darwin")
    export([parse_darwin_json(path)], tmp_path / "export")
    for i, lab in enumerate(labels):
        out = np.fromfile(
            tmp_path / "export" / "semantickitti_07" / "labels" / f"{i:06d}.label",
            "<u4",
        )
        assert np.array_equal(out, lab)
    ids = json.loads((tmp_path / "export" / "class_ids.json").read_text())
    assert ids["class_300"] == 300 and ids["car"] == 10


def test_exporter_new_class_ids(tmp_path):
    seq, labels = _sequence(tmp_path, with_poses=False, n=1)
    (af,) = parse_semantic_kitti(seq / "labels", class_names={10: "Car"})
    assert af.slots[0].metadata["coordinate_frame"] == "sensor"
    export([af], tmp_path / "export")
    ids = json.loads((tmp_path / "export" / "class_ids.json").read_text())
    assert ids["Car"] == 260  # not a SemanticKITTI name: new id from 260
    assert ids["class_40"] == 40


def test_registered_importer_triggers_once_per_directory(tmp_path):
    seq, _ = _sequence(tmp_path)
    results = [parse_path(p) for p in sorted(seq.glob("**/*"))]
    parsed = [r for r in results if r is not None]
    assert len(parsed) == 1 and parsed[0][0].filename == "semantickitti_07.lidar.zip"
    assert parse_path(seq / "labels") is None
