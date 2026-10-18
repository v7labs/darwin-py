import json

import numpy as np
import pytest

from darwin.importer import get_importer
from darwin.lidar import geometry as g
from darwin.lidar.scene import read_scene

pd = pytest.importorskip("pandas")

K = {"fx": 30.0, "fy": 30.0, "cx": 20.0, "cy": 15.0}


def _pose_json(pose):
    w, x, y, z = g.rot_to_quat(pose)
    t = pose[:3, 3]
    return {
        "position": {"x": t[0], "y": t[1], "z": t[2]},
        "heading": {"w": w, "x": x, "y": y, "z": z},
    }


def _lidar_pose(f):
    return g.make_pose(g.euler_to_rot(0, 0, 0.2 * f), (500 + 2 * f, 300, 10))


def _devkit_corners(box):
    # pandaset-devkit geometry.center_box_to_corners
    px, py, pz, dx, dy, dz, yaw = box
    c = np.array(
        [
            [sx * dx / 2, sy * dy / 2, sz * dz / 2]
            for sz in (-1, 1)
            for sx, sy in ((1, 1), (1, -1), (-1, -1), (-1, 1))
        ]
    )
    r = g.euler_to_rot(0, 0, yaw)
    return c @ r.T + [px, py, pz]


@pytest.fixture
def seq(tmp_path):
    from PIL import Image

    d = tmp_path / "002"
    rng = np.random.default_rng(0)
    (d / "lidar").mkdir(parents=True)
    (d / "annotations" / "cuboids").mkdir(parents=True)
    (d / "annotations" / "semseg").mkdir(parents=True)
    cam = d / "camera" / "front_camera"
    cam.mkdir(parents=True)
    # camera z forward = lidar heading (+x of the lidar pose), x right, y down
    cam_axes = np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0.0]])
    clouds = []
    for f in range(2):
        n = 20
        xyz = rng.uniform(-30, 30, (n, 3)) + _lidar_pose(f)[:3, 3]
        df = pd.DataFrame(
            {
                "x": xyz[:, 0],
                "y": xyz[:, 1],
                "z": xyz[:, 2],
                "i": rng.uniform(0, 255, n),
                "t": 0.0,
                "d": [0] * 15 + [1] * 5,
            }
        )
        df.to_pickle(d / "lidar" / f"{f:02d}.pkl.gz")
        clouds.append(df)
        Image.new("RGB", (40, 30)).save(cam / f"{f:02d}.jpg")
        cuboids = pd.DataFrame(
            {
                "uuid": ["car-1", "car-1"] + (["ped-2"] if f else []),
                "label": ["Car", "Car"] + (["Pedestrian"] if f else []),
                "yaw": [0.0, 0.1] + ([1.0] if f else []),
                "position.x": [510.0, 510.4] + ([495.0] if f else []),
                "position.y": [305.0, 305.0] + ([290.0] if f else []),
                "position.z": [9.0, 9.0] + ([9.5] if f else []),
                "dimensions.x": [2.0, 2.0] + ([0.7] if f else []),
                "dimensions.y": [5.0, 5.0] + ([0.6] if f else []),
                "dimensions.z": [1.6, 1.6] + ([1.8] if f else []),
                "cuboids.sensor_id": [0, 1] + ([-1] if f else []),
            }
        )
        cuboids.to_pickle(d / "annotations" / "cuboids" / f"{f:02d}.pkl.gz")
        pd.DataFrame({"class": [5] * 10 + [7] * 3 + [5] * 7}).to_pickle(
            d / "annotations" / "semseg" / f"{f:02d}.pkl.gz"
        )
    (d / "annotations" / "semseg" / "classes.json").write_text(
        json.dumps({"5": "Road", "7": "Car"})
    )
    (d / "lidar" / "poses.json").write_text(
        json.dumps([_pose_json(_lidar_pose(f)) for f in range(2)])
    )
    (d / "lidar" / "timestamps.json").write_text(
        json.dumps([1557540000.1, 1557540000.2])
    )
    (cam / "intrinsics.json").write_text(json.dumps(K))
    cam_poses = [_lidar_pose(f) @ g.make_pose(cam_axes, (1, 0, 0.5)) for f in range(2)]
    (cam / "poses.json").write_text(json.dumps([_pose_json(p) for p in cam_poses]))
    return d, clouds, cam_poses


def test_build_pandaset(seq, tmp_path, check_calibration):
    from darwin.lidar.pandaset import build_pandaset

    d, clouds, cam_poses = seq
    scene = read_scene(build_pandaset(d, tmp_path / "out"))
    assert scene.path.name == "pandaset_002.lidar.zip"
    m = scene.manifest
    assert (
        m["coordinate_frame"] == "world" and m["cameras"][0]["name"] == "front_camera"
    )
    assert [f["timestamp"] for f in m["frames"]] == pytest.approx([0, 0.1])
    origin = _lidar_pose(0)[:3, 3]
    assert m["origin"] == pytest.approx(origin.tolist())
    assert check_calibration(m)["front_camera"]["distortion"] == {"model": "pinhole"}
    for f, df in enumerate(clouds):
        assert np.allclose(
            scene.ego_pose(f), g.translation(-origin) @ _lidar_pose(f), atol=1e-6
        )
        xyz = df[["x", "y", "z"]].to_numpy() - origin
        assert np.abs(scene.points(f).xyz - xyz).max() < 0.006
    ahead = g.transform_points(cam_poses[1], np.array([[0, 0, 10.0]]))[0] - origin
    u, v, w = (
        np.array(m["frames"][1]["images"]["front_camera"]["world_to_image"])
        @ np.r_[ahead, 1]
    )
    sx, sy = m["cameras"][0]["width"] / 40, m["cameras"][0]["height"] / 30
    assert w > 0 and np.allclose([u / w, v / w], [20 * sx, 15 * sy], atol=1e-3)
    only64 = read_scene(
        build_pandaset(d, tmp_path / "s0.lidar.zip", cameras=[], sensor=0)
    )
    assert len(only64.points(0).xyz) == 15


def test_parse_pandaset_cuboids_and_semseg(seq):
    from darwin.lidar.pandaset import parse_pandaset

    d, _, _ = seq
    [af] = parse_pandaset(d)
    assert af.filename == "pandaset_002.lidar.zip"

    def of_type(t):
        return {
            a.annotation_class.name: a
            for a in af.annotations
            if a.annotation_class.annotation_type == t
        }

    boxes, masks = of_type("cuboid_3d"), of_type("point_mask_3d")
    car, ped = boxes["Car"], boxes["Pedestrian"]
    assert sorted(car.frames) == [0, 1] and sorted(ped.frames) == [1]
    origin = _lidar_pose(0)[:3, 3]
    box = car.frames[0].data  # the sensor_id=1 duplicate is dropped
    assert box["dimensions"] == {"x": 5.0, "y": 2.0, "z": 1.6}
    assert box["rotation"]["z"] == pytest.approx(np.pi / 2)
    corners = g.box_corners(box) + origin
    expected = _devkit_corners((510, 305, 9, 2, 5, 1.6, 0.0))
    assert np.allclose(sorted(map(tuple, corners)), sorted(map(tuple, expected)))
    assert ped.frames[1].get_sub("instance_id").data == 2
    assert set(masks) == {"Road", "Car"}
    assert masks["Road"].frames[0].data == {"point_count": 20, "ranges": [0, 10, 13, 7]}
    assert masks["Car"].frames[1].data == {"point_count": 20, "ranges": [10, 3]}
    assert not masks["Road"].interpolated
    [only64] = parse_pandaset(d, sensor=0)
    road64 = next(a for a in only64.annotations if a.annotation_class.name == "Road")
    assert road64.frames[0].data == {"point_count": 15, "ranges": [0, 10, 13, 2]}


def test_registered_importer(seq):
    d, _, _ = seq
    importer = get_importer("pandaset")
    cuboids = d / "annotations" / "cuboids"
    assert importer(cuboids / "01.pkl.gz") is None
    assert importer(d / "annotations" / "semseg" / "00.pkl.gz") is None
    assert importer(d / "lidar" / "00.pkl.gz") is None
    [af] = importer(cuboids / "00.pkl.gz")
    assert af.slots[0].metadata["coordinate_frame"] == "world"
