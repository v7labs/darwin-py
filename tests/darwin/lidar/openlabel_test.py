import json

import numpy as np
import pytest

from darwin.exporter import get_exporter
from darwin.importer import get_importer
from darwin.lidar import geometry as g
from darwin.lidar.darwin_json import instance_id_of, write_darwin_json
from darwin.lidar.openlabel import export_openlabel, parse_openlabel
from darwin.utils import parse_darwin_json

LIDAR_IN_EGO = g.make_pose(g.euler_to_rot(0, 0, 0.0), (1.0, 0.0, 1.8))
CAR_Q = g.rot_to_quat(g.euler_to_rot(0.0, 0.0, 0.4))  # w, x, y, z


def odom_from_ego(f):
    return g.make_pose(g.euler_to_rot(0.01 * f, 0, 0.1 * f), (2.0 * f, 0.5 * f, 0))


def _flat(m):
    return np.asarray(m).ravel().tolist()


def _openlabel(tmp_path, car_val=None):
    w, x, y, z = CAR_Q
    car_val = car_val or [10, -1, 0.2, x, y, z, w, 4.5, 1.9, 1.6]
    frames = {
        str(f): {
            "frame_properties": {
                "timestamp": 100 + f / 10,
                "transforms": {
                    "ego_to_odom": {
                        "src": "ego",
                        "dst": "odom",
                        "transform_src_to_dst": {"matrix4x4": _flat(odom_from_ego(f))},
                    }
                },
            },
            "objects": {
                "0": {
                    "object_data": {
                        "cuboid": [
                            {
                                "name": "box",
                                "val": car_val,
                                "coordinate_system": "lidar",
                            }
                        ],
                        "bbox": [{"name": "2d", "val": [1, 2, 3, 4]}],
                        "text": [{"name": "note", "val": "x"}],
                    }
                }
            },
        }
        for f in range(3)
    }
    frames["1"]["objects"]["2"] = {
        "object_data": {
            "poly3d": [
                {
                    "name": "zone",
                    "val": [0, 0, 0, 1, 0, 0, 1, 1, 0],
                    "closed": True,
                    "coordinate_system": "ego",
                }
            ]
        }
    }
    for f in (0, 2):
        frames[str(f)]["objects"]["3"] = {
            "object_data": {
                "point3d": [
                    {"name": "p", "val": [5, 5, 0], "coordinate_system": "lidar"}
                ]
            }
        }
    data = {
        "openlabel": {
            "metadata": {"schema_version": "1.0.0", "tagged_file": "drive.lidar.zip"},
            "coordinate_systems": {
                "odom": {"type": "scene_cs", "parent": "", "children": ["ego"]},
                "ego": {"type": "local_cs", "parent": "odom", "children": ["lidar"]},
                "lidar": {
                    "type": "sensor_cs",
                    "parent": "ego",
                    "pose_wrt_parent": {
                        "quaternion": [0, 0, 0, 1],
                        "translation": [1.0, 0.0, 1.8],
                    },
                },
            },
            "objects": {
                "0": {
                    "name": "car1",
                    "type": "Car",
                    "frame_intervals": [{"frame_start": 0, "frame_end": 2}],
                },
                "1": {
                    "name": "lane",
                    "type": "Lane",
                    "frame_intervals": [{"frame_start": 0, "frame_end": 2}],
                    "object_data": {
                        "poly3d": [
                            {
                                "name": "line",
                                "val": [0, 0, 0, 10, 0, 0, 20, 1, 0],
                                "closed": False,
                                "coordinate_system": "odom",
                            }
                        ]
                    },
                },
                "2": {"name": "zone", "type": "Zone"},
                "3": {"name": "pole", "type": "Pole"},
                "4": {
                    "name": "sign",
                    "type": "Sign",
                    "object_data": {
                        "point3d": [
                            {
                                "name": "s",
                                "val": [3, 0, 0],
                                "coordinate_system": "lidar",
                            }
                        ]
                    },
                },
            },
            "frames": frames,
        }
    }
    path = tmp_path / "drive.openlabel.json"
    path.write_text(json.dumps(data))
    return path


def _numbers(obj):
    if isinstance(obj, dict):
        return [v for k in sorted(obj) for v in _numbers(obj[k])]
    if isinstance(obj, list):
        return [v for x in obj for v in _numbers(x)]
    return [float(obj)]


def _summary(af):
    out = []
    for a in af.annotations:
        out.append(
            (
                a.annotation_class.name,
                a.annotation_class.annotation_type,
                a.segments,
                instance_id_of(a),
                {f: _numbers(fa.data) for f, fa in a.frames.items()},
            )
        )
    return out


def test_import_geometry_and_frames(tmp_path):
    (af,) = parse_openlabel(_openlabel(tmp_path))
    assert af.filename == "drive.lidar.zip"
    meta = af.slots[0].metadata
    assert meta["coordinate_frame"] == "world"
    assert np.allclose(meta["frames"][2]["ego_pose"], odom_from_ego(2))
    assert meta["frames"][1]["timestamp"] == pytest.approx(100.1)
    by_class = {a.annotation_class.name: a for a in af.annotations}
    assert set(by_class) == {"Car", "Lane", "Zone", "Pole", "Sign"}

    car = by_class["Car"]
    assert car.annotation_class.annotation_type == "cuboid_3d" and sorted(
        car.frames
    ) == [0, 1, 2]
    expected = (
        odom_from_ego(1)
        @ LIDAR_IN_EGO
        @ g.make_pose(g.euler_to_rot(0, 0, 0.4), (10, -1, 0.2))
    )
    got = g.cuboid_to_pose(car.frames[1].data)
    assert np.allclose(got, expected)
    assert car.frames[1].data["dimensions"] == {"x": 4.5, "y": 1.9, "z": 1.6}
    assert instance_id_of(car) == 1

    lane = by_class[
        "Lane"
    ]  # static in the target frame: one keyframe over the interval
    assert lane.annotation_class.annotation_type == "polyline_3d"
    assert (
        sorted(lane.frames) == [0] and lane.segments == [[0, 3]] and lane.interpolated
    )
    assert by_class["Zone"].annotation_class.annotation_type == "polygon_3d"
    zone_pt = by_class["Zone"].frames[1].data["path"][2]
    assert np.allclose(
        [zone_pt[k] for k in "xyz"],
        g.transform_points(odom_from_ego(1), [[1, 1, 0]])[0],
    )
    assert by_class["Pole"].segments == [[0, 1], [2, 3]]

    sign = by_class["Sign"]  # static in the moving lidar frame: expanded to every frame
    assert sorted(sign.frames) == [0, 1, 2]
    p = sign.frames[2].data
    assert np.allclose(
        [p[k] for k in "xyz"],
        g.transform_points(odom_from_ego(2) @ LIDAR_IN_EGO, [[3, 0, 0]])[0],
    )


def test_round_trip_through_darwin_json(tmp_path):
    (af,) = parse_openlabel(_openlabel(tmp_path))
    back = parse_darwin_json(write_darwin_json(af, tmp_path / "darwin"))
    (out,) = export_openlabel([back], tmp_path / "ol")
    assert out.name == "drive.openlabel.json"
    (again,) = parse_openlabel(out)
    assert again.filename == af.filename
    a, b = _summary(af), _summary(again)
    assert [x[:4] for x in a] == [x[:4] for x in b]
    for x, y in zip(a, b):
        assert x[4].keys() == y[4].keys()
        for f in x[4]:
            assert np.allclose(x[4][f], y[4][f], atol=1e-6)
    for m1, m2 in zip(
        af.slots[0].metadata["frames"], again.slots[0].metadata["frames"]
    ):
        assert np.allclose(m1["ego_pose"], m2["ego_pose"])
        assert m1["timestamp"] == pytest.approx(m2["timestamp"])


def test_euler_cuboid_matches_quaternion(tmp_path):
    (q,) = parse_openlabel(_openlabel(tmp_path))
    (e,) = parse_openlabel(
        _openlabel(tmp_path, [10, -1, 0.2, 0, 0, 0.4, 4.5, 1.9, 1.6])
    )
    assert np.allclose(
        _numbers(q.annotations[0].frames[1].data),
        _numbers(e.annotations[0].frames[1].data),
    )


def test_sensor_frame_without_transforms(tmp_path):
    data = {
        "openlabel": {
            "metadata": {"schema_version": "1.0.0"},
            "objects": {"0": {"type": "Car"}},
            "frames": {
                "0": {
                    "objects": {
                        "0": {
                            "object_data": {
                                "cuboid": [{"val": [1, 2, 3, 0, 0, 0, 4, 2, 1]}]
                            }
                        }
                    }
                }
            },
        }
    }
    path = tmp_path / "single.json"
    path.write_text(json.dumps(data))
    (af,) = parse_openlabel(path)
    assert af.filename == "single.lidar.zip"
    assert af.slots[0].metadata["coordinate_frame"] == "sensor"
    assert af.annotations[0].frames[0].data["position"] == {
        "x": 1.0,
        "y": 2.0,
        "z": 3.0,
    }


def test_registered_importer_and_exporter(tmp_path):
    importer = get_importer("openlabel")
    path = _openlabel(tmp_path)
    assert len(importer(path)) == 1
    darwin = tmp_path / "item.json"
    darwin.write_text(json.dumps({"version": "2.0", "openlabel": {}}))
    assert importer(darwin) is None
    assert importer(tmp_path) is None
    get_exporter("openlabel")(iter(parse_openlabel(path)), tmp_path / "x")
    assert (tmp_path / "x" / "drive.openlabel.json").exists()
