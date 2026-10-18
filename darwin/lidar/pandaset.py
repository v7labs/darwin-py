"""
PandaSet sequences: scene packages, cuboid and semantic segmentation import.

PandaSet stores points, cuboids and poses in one world frame. Scene frame: that world translated
so the first lidar pose is the origin. Ego frame: the Pandar64 lidar pose (``lidar/poses.json``).
Lidar frames and labels are pandas pickles (``.pkl.gz``): unpickling runs code, so only read
trusted data. Needs ``pandas``.

Cuboids (PandaSet devkit): ``dimensions.x`` = width, ``dimensions.y`` = length, ``yaw`` = 0 means
the length axis points along +y, so Darwin ``rotation.z = yaw + pi/2`` and length = ``dimensions.y``.
"""

import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence

import numpy as np
from natsort import natsorted

import darwin.datatypes as dt
from darwin.lidar import geometry as g
from darwin.lidar.darwin_json import make_lidar_file, make_track, mask_to_ranges
from darwin.lidar.pointcloud import PathLike, missing_dependency
from darwin.lidar.scene import CameraImage, Frame, package_path, write_scene

CAMERAS = (
    "front_camera",
    "front_left_camera",
    "front_right_camera",
    "left_camera",
    "right_camera",
    "back_camera",
)


def _pickle(path: Path) -> Any:
    try:
        import pandas
    except ImportError:
        raise missing_dependency("pandas", "lidar_pandaset") from None
    return pandas.read_pickle(path)  # trusted data only: pickles execute code


def _files(d: Path) -> List[Path]:
    return natsorted(d.glob("*.pkl.gz"), key=lambda p: p.name)


def _pose(p: Dict[str, Dict[str, float]]) -> np.ndarray:
    h, t = p["heading"], p["position"]
    return g.make_pose(
        g.quat_to_rot(h["w"], h["x"], h["y"], h["z"]), (t["x"], t["y"], t["z"])
    )


def _sequence(sequence_dir: PathLike) -> tuple:
    seq = Path(sequence_dir)
    world_from_lidar = np.array(
        [_pose(p) for p in json.loads((seq / "lidar" / "poses.json").read_text())]
    )
    scene_from_world = g.translation(-world_from_lidar[0, :3, 3])
    ts_path = seq / "lidar" / "timestamps.json"
    ts = json.loads(ts_path.read_text()) if ts_path.exists() else None
    return seq, scene_from_world, scene_from_world @ world_from_lidar, ts


def _sensor_rows(frame: Any, sensor: Optional[int]) -> np.ndarray:
    d = np.asarray(frame["d"]) if "d" in frame else np.zeros(len(frame))
    return np.ones(len(frame), bool) if sensor is None else d == sensor


def build_pandaset(
    sequence_dir: PathLike,
    output: PathLike,
    cameras: Optional[Sequence[str]] = None,
    image_scale: float = 0.5,
    sensor: Optional[int] = None,
) -> Path:
    """
    One PandaSet sequence -> ``pandaset_<seq>.lidar.zip`` (world frame). ``sensor``: ``None`` keeps
    both lidars in file order, ``0`` only the Pandar64, ``1`` only the PandarGT; pass the same value
    to :func:`parse_pandaset` so point masks index the same points.
    """
    seq, scene_from_world, ego, ts = _sequence(sequence_dir)
    world_from_scene = g.invert(scene_from_world)
    cams = []
    for cam in cameras or CAMERAS:
        d = seq / "camera" / cam
        if not (d / "poses.json").exists():
            continue
        i = json.loads((d / "intrinsics.json").read_text())
        k = np.array([[i["fx"], 0, i["cx"]], [0, i["fy"], i["cy"]], [0, 0, 1]])
        poses = [_pose(p) for p in json.loads((d / "poses.json").read_text())]
        files = natsorted(d.glob("*.jpg"), key=lambda p: p.name)
        cams.append((cam, files, k, [g.invert(p) @ world_from_scene for p in poses]))

    def frames() -> Iterator[Frame]:
        for f, path in enumerate(_files(seq / "lidar")):
            df = _pickle(path)
            keep = _sensor_rows(df, sensor)
            xyz = np.stack([np.asarray(df[c], float) for c in "xyz"], 1)[keep]
            images = {
                cam: CameraImage(files[f], None, k, cfw[f], {"model": "pinhole"})
                for cam, files, k, cfw in cams
                if f < len(files) and f < len(cfw)
            }
            yield Frame(
                g.transform_points(scene_from_world, xyz),
                np.asarray(df["i"], float)[keep] if "i" in df else None,
                ts[f] if ts else f / 10,
                ego[f],
                images,
            )

    return write_scene(
        package_path(output, f"pandaset_{seq.name}"),
        frames(),
        name=f"PandaSet {seq.name}",
        fps=10,
        coordinate_frame="world",
        image_scale=image_scale,
        origin=world_from_scene[:3, 3],
    )


def parse_pandaset(
    sequence_dir: PathLike, semseg: bool = True, sensor: Optional[int] = None
) -> List[dt.AnnotationFile]:
    """
    One sequence -> one ``AnnotationFile`` for ``pandaset_<seq>.lidar.zip``: a ``cuboid_3d`` track
    per cuboid ``uuid`` (scene frame, ``instance_id`` = order of first appearance) and, when
    ``semseg``, a ``point_mask_3d`` track per semantic class. Moving objects in the lidar overlap
    are labeled once per lidar (``cuboids.sensor_id``): the Pandar64 copy is kept unless
    ``sensor=1``. ``sensor`` must match the value used for :func:`build_pandaset`.
    """
    seq, scene_from_world, ego, ts = _sequence(sequence_dir)
    n = len(ego)
    keep_sensor = 1 if sensor == 1 else 0
    tracks: Dict[str, Dict[str, Any]] = {}
    for f, path in enumerate(_files(seq / "annotations" / "cuboids")):
        df = _pickle(path)
        sid = np.asarray(df["cuboids.sensor_id"]) if "cuboids.sensor_id" in df else None
        for r in range(len(df)):
            if sid is not None and sid[r] not in (-1, keep_sensor):
                continue
            row = {c: df[c].iloc[r] for c in df.columns}
            world_box = g.make_pose(
                g.euler_to_rot(0, 0, float(row["yaw"]) + np.pi / 2),
                [float(row[f"position.{a}"]) for a in "xyz"],
            )
            dims = (row["dimensions.y"], row["dimensions.x"], row["dimensions.z"])
            track = tracks.setdefault(
                str(row["uuid"]), {"label": str(row["label"]), "frames": {}}
            )
            track["frames"][f] = g.pose_to_cuboid(scene_from_world @ world_box, dims)
    annotations = [
        make_track(t["label"], "cuboid_3d", t["frames"], instance_id=i + 1)
        for i, t in enumerate(tracks.values())
    ]
    semseg_dir = seq / "annotations" / "semseg"
    if semseg and semseg_dir.exists():
        names = json.loads((semseg_dir / "classes.json").read_text())
        lidar = _files(seq / "lidar")
        masks: Dict[int, Dict[int, Dict[str, Any]]] = {}
        for f, path in enumerate(_files(semseg_dir)):
            classes = np.asarray(_pickle(path)["class"]).ravel()
            if sensor is not None:
                classes = classes[_sensor_rows(_pickle(lidar[f]), sensor)]
            for c in np.unique(classes):
                runs = mask_to_ranges(classes == c)
                masks.setdefault(int(c), {})[f] = {
                    "point_count": len(classes),
                    "ranges": runs,
                }
        annotations += [
            make_track(names.get(str(c), f"class_{c}"), "point_mask_3d", frames)
            for c, frames in sorted(masks.items())
        ]
    return [
        make_lidar_file(
            f"pandaset_{seq.name}.lidar.zip",
            annotations,
            n,
            "world",
            ego_poses=ego,
            timestamps=[t - ts[0] for t in ts] if ts else None,
            fps=10,
        )
    ]
