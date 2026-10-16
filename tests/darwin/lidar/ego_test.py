import json

import numpy as np
import pytest

from darwin.exporter import get_exporter
from darwin.lidar import geometry as g
from darwin.lidar.darwin_json import make_lidar_file, make_track
from darwin.lidar.ego import ego_frame_view, export_ego

# ego at (10, 5, 0) heading +90 deg, then moving 1 m per frame along +y
POSES = [g.make_pose(g.euler_to_rot(0, 0, np.pi / 2), (10, 5 + f, 0)) for f in range(2)]


def _box(x, y, yaw):
    return {
        "position": {"x": x, "y": y, "z": 1.0},
        "dimensions": {"x": 4.0, "y": 2.0, "z": 1.5},
        "rotation": {"x": 0.02, "y": 0.0, "z": yaw},
    }


def _file(frame="world", poses=POSES):
    car = make_track(
        "Car",
        "cuboid_3d",
        {0: _box(10, 7, np.pi / 2 + 0.1), 1: _box(10, 9, np.pi / 2)},
        instance_id=4,
    )
    pole = make_track("Pole", "keypoint_3d", {1: {"x": 11.0, "y": 6.0, "z": 0.0}})
    mask = make_track(
        "Road", "point_mask_3d", {0: {"point_count": 5, "ranges": [0, 2]}}
    )
    return make_lidar_file(
        "drive.lidar.zip", [car, pole, mask], 2, frame, ego_poses=poses
    )


def test_ego_view_known_transforms():
    view = ego_frame_view(_file())
    assert view["item"] == "drive.lidar.zip" and view["coordinate_frame"] == "ego"
    f0, f1 = view["frames"]
    assert np.allclose(f0["ego_pose"], POSES[0])
    car0 = f0["annotations"][0]
    assert car0["name"] == "Car" and car0["instance_id"] == 4
    assert [car0["cuboid_3d"]["position"][k] for k in "xyz"] == pytest.approx([2, 0, 1])
    assert car0["cuboid_3d"]["rotation"]["z"] == pytest.approx(0.1)
    car1 = f1["annotations"][0]["cuboid_3d"]
    assert [car1["position"][k] for k in "xyz"] == pytest.approx([3, 0, 1])
    pole = f1["annotations"][1]["keypoint_3d"]
    assert [pole[k] for k in "xyz"] == pytest.approx([0, -1, 0])
    assert f0["annotations"][1]["point_mask_3d"] == {"point_count": 5, "ranges": [0, 2]}
    flat = ego_frame_view(_file(), yaw_only=True)["frames"][0]["annotations"][0][
        "cuboid_3d"
    ]
    assert flat["rotation"]["x"] == 0 and flat["rotation"]["z"] == pytest.approx(
        0.1, abs=1e-3
    )


def test_sensor_items_pass_through():
    view = ego_frame_view(_file("sensor", None))
    assert view["frames"][0]["ego_pose"] is None
    assert view["frames"][0]["annotations"][0]["cuboid_3d"] == _box(
        10, 7, np.pi / 2 + 0.1
    )


def test_world_item_without_poses_raises():
    af = _file()
    af.slots[0].metadata["frames"] = []
    with pytest.raises(ValueError, match="ego_pose"):
        ego_frame_view(af)


def test_export_ego_and_registered_exporter(tmp_path):
    (path,) = export_ego([_file()], tmp_path)
    assert path.name == "drive.ego.json"
    assert len(json.loads(path.read_text())["frames"]) == 2
    get_exporter("lidar_ego")(iter([_file()]), tmp_path / "reg")
    assert (tmp_path / "reg" / "drive.ego.json").exists()
