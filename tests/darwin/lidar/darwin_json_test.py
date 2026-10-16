import copy
import json

import darwin.datatypes as dt
from darwin.importer.importer import _get_annotation_data
from darwin.lidar.darwin_json import (
    frame_objects,
    make_lidar_file,
    make_track,
    to_darwin_json,
    write_darwin_json,
)
from darwin.utils import parse_darwin_json

CUBOID = {
    "dimensions": {"x": 4.6, "y": 1.95, "z": 1.7},
    "position": {"x": 18.0, "y": -3.1, "z": 0.9},
    "rotation": {"x": 0.0, "y": 0.0, "z": 1.57},
}

# Shapes copied from a real Darwin export of a LiDAR item (pointcloud slot, the 5 3D types)
EXPORT = {
    "version": "2.0",
    "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json",
    "item": {
        "name": "scene.lidar.zip",
        "path": "/",
        "source_info": {"item_id": "01a1420b-5c28-d6ba-73c4-110b7c12d0d9"},
        "slots": [
            {
                "type": "pointcloud",
                "slot_name": "0",
                "fps": 10.0,
                "thumbnail_url": "http://localhost/thumbnail",
                "source_files": [
                    {"file_name": "scene.lidar.zip", "url": "http://localhost/u"}
                ],
                "frame_count": 3,
                "metadata": {
                    "coordinate_frame": "world",
                    "frames": [
                        {
                            "timestamp": t / 10,
                            "ego_pose": [
                                [1, 0, 0, t],
                                [0, 1, 0, 0],
                                [0, 0, 1, 0],
                                [0, 0, 0, 1],
                            ],
                        }
                        for t in range(3)
                    ],
                },
            }
        ],
    },
    "annotations": [
        {
            "frames": {
                "0": {
                    "cuboid_3d": CUBOID,
                    "keyframe": True,
                    "instance_id": {"value": 7},
                },
                "1": {
                    "cuboid_3d": CUBOID,
                    "keyframe": False,
                    "instance_id": {"value": 7},
                },
                "2": {
                    "cuboid_3d": CUBOID,
                    "keyframe": True,
                    "instance_id": {"value": 7},
                },
            },
            "global_sub_types": {},
            "id": "0f3f1456-bd29-4d67-af18-cc63beb0083f",
            "interpolate_algorithm": "linear-1.1",
            "interpolated": True,
            "name": "Car",
            "properties": [],
            "ranges": [[0, 3]],
            "slot_names": ["0"],
        },
        {
            "frames": {
                "0": {
                    "keyframe": True,
                    "polyline_3d": {
                        "path": [{"x": 1, "y": 2, "z": 3}, {"x": 4, "y": 5, "z": 6}]
                    },
                }
            },
            "global_sub_types": {},
            "id": "7468c308-c11e-48e3-8de5-ec2d24c5f325",
            "interpolate_algorithm": "linear-1.1",
            "interpolated": True,
            "name": "Lane line",
            "properties": [],
            "ranges": [[0, 1]],
            "slot_names": ["0"],
        },
        {
            "frames": {
                "1": {
                    "keyframe": True,
                    "polygon_3d": {
                        "path": [
                            {"x": 0, "y": 0, "z": 0},
                            {"x": 1, "y": 0, "z": 0},
                            {"x": 1, "y": 1, "z": 0},
                        ]
                    },
                    "attributes": ["parked"],
                    "text": {"text": "hello"},
                }
            },
            "global_sub_types": {},
            "id": "8468c308-c11e-48e3-8de5-ec2d24c5f325",
            "interpolate_algorithm": "linear-1.1",
            "interpolated": True,
            "name": "Zone",
            "properties": [],
            "ranges": [[1, 2]],
            "slot_names": ["0"],
        },
        {
            "frames": {
                "2": {"keyframe": True, "keypoint_3d": {"x": 1.5, "y": 2.5, "z": 0.1}}
            },
            "global_sub_types": {},
            "id": "9468c308-c11e-48e3-8de5-ec2d24c5f325",
            "interpolate_algorithm": "linear-1.1",
            "interpolated": True,
            "name": "Pole",
            "properties": [],
            "ranges": [[2, 3]],
            "slot_names": ["0"],
        },
        {
            "frames": {
                "0": {
                    "keyframe": True,
                    "point_mask_3d": {"point_count": 100, "ranges": [3, 2, 10, 5]},
                }
            },
            "global_sub_types": {},
            "id": "fa199445-013b-4fb3-a56d-ead10dd35fc6",
            "interpolate_algorithm": "linear-1.1",
            "name": "Building",
            "properties": [],
            "ranges": [[0, 1]],
            "slot_names": ["0"],
        },
    ],
    "properties": [],
}


def _parse(tmp_path, data):
    path = tmp_path / "scene.lidar.json"
    path.write_text(json.dumps(data))
    return parse_darwin_json(path)


def test_export_parses_all_3d_types(tmp_path):
    f = _parse(tmp_path, EXPORT)
    assert [a.annotation_class.annotation_type for a in f.annotations] == list(
        dt.LIDAR_ANNOTATION_TYPES
    )
    assert f.slots[0].type == "pointcloud"
    assert f.slots[0].metadata["coordinate_frame"] == "world"
    assert not f.is_video  # pointcloud items are never split into frames


def test_export_parse_serialize_is_identical(tmp_path):
    out = to_darwin_json(_parse(tmp_path, EXPORT))
    assert out["annotations"] == EXPORT["annotations"]
    assert out["item"]["slots"] == EXPORT["item"]["slots"]
    assert out["item"]["name"] == EXPORT["item"]["name"]
    assert out["properties"] == EXPORT["properties"]


def test_import_payload_matches_backend_contract(tmp_path):
    f = _parse(tmp_path, EXPORT)
    data = _get_annotation_data(f.annotations[0], "1", {})
    assert set(data["frames"]) == {0, 2}  # only keyframes
    assert data["frames"][0]["cuboid_3d"] == CUBOID
    assert data["frames"][0]["instance_id"] == {"value": 7}
    assert data["segments"] == [[0, 3]]
    mask = _get_annotation_data(f.annotations[4], "2", {})
    assert mask["frames"][0]["point_mask_3d"] == {
        "point_count": 100,
        "ranges": [3, 2, 10, 5],
    }


def test_only_keyframes_import_payload_parses(tmp_path):
    data = copy.deepcopy(EXPORT)
    for a in data["annotations"]:
        a["only_keyframes"] = True
    f = _parse(tmp_path, data)
    assert len(f.annotations) == 5


def test_make_track_and_write_round_trip(tmp_path):
    track = make_track(
        "Car",
        "cuboid_3d",
        {0: CUBOID, 1: CUBOID, 5: CUBOID},
        instance_id=3,
        attributes={1: ["moving"]},
    )
    assert track.segments == [[0, 2], [5, 6]]
    mask = make_track(
        "Road", "point_mask_3d", {0: {"point_count": 4, "ranges": [0, 4]}}
    )
    assert not mask.interpolated
    af = make_lidar_file("s.lidar.zip", [track, mask], 6, "sensor")
    path = write_darwin_json(af, tmp_path)
    assert path.name == "s.lidar.json"
    back = parse_darwin_json(path)
    assert to_darwin_json(back) == to_darwin_json(af)
    objs = frame_objects(back)
    assert sorted(objs) == [0, 1, 5]
    assert objs[1][0].instance_id == 3 and objs[1][0].attributes == ["moving"]


def test_makers():
    a = dt.make_cuboid_3d("Car", (1, 2, 3), (4, 2, 1.5), (0, 0, 0.5))
    assert a.data["position"] == {"x": 1.0, "y": 2.0, "z": 3.0}
    assert dt.make_point_mask_3d("Road", 10, [0, 2]).data == {
        "point_count": 10,
        "ranges": [0, 2],
    }
    assert (
        dt.make_polygon_3d("Zone", [(0, 0, 0)]).annotation_class.annotation_type
        == "polygon_3d"
    )
    assert dt.make_keypoint_3d("Pole", {"x": 1, "y": 2, "z": 3}).data == {
        "x": 1.0,
        "y": 2.0,
        "z": 3.0,
    }
    assert (
        dt.make_polyline_3d("Lane", [(0, 0, 0), (1, 1, 1)]).data["path"][1]["z"] == 1.0
    )
