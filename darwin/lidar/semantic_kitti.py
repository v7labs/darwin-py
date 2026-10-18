"""
SemanticKITTI / KITTI odometry.

Layout: ``sequences/<seq>/{velodyne/*.bin, labels/*.label, image_2/*.png, calib.txt, poses.txt,
times.txt}``. ``.label`` files hold one uint32 per point (semantic = lower 16 bits, instance =
upper 16 bits), in the point order of the matching ``.bin``.

- :func:`build_kitti_odometry`: sequence -> ``semantickitti_<seq>.lidar.zip`` (world frame from
  ``poses.txt`` + ``calib.txt``, else sensor frame).
- :func:`parse_semantic_kitti`: ``labels/`` -> ``point_mask_3d`` annotations.
- :func:`export_semantic_kitti`: Darwin point masks -> ``.label`` files.
"""

import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np
from natsort import natsorted

import darwin.datatypes as dt
from darwin.lidar import geometry as g
from darwin.lidar.darwin_json import (
    frame_objects,
    indices_to_ranges,
    make_lidar_file,
    make_track,
    ranges_to_indices,
)
from darwin.lidar.generic import cloud_files, load_poses, world_to_scene
from darwin.lidar.pointcloud import PathLike, read_bin
from darwin.lidar.scene import CameraImage, Frame, package_path, write_scene

#: semantic-kitti.yaml ``labels``
CLASS_NAMES: Dict[int, str] = {
    0: "unlabeled", 1: "outlier", 10: "car", 11: "bicycle", 13: "bus", 15: "motorcycle",
    16: "on-rails", 18: "truck", 20: "other-vehicle", 30: "person", 31: "bicyclist",
    32: "motorcyclist", 40: "road", 44: "parking", 48: "sidewalk", 49: "other-ground",
    50: "building", 51: "fence", 52: "other-structure", 60: "lane-marking", 70: "vegetation",
    71: "trunk", 72: "terrain", 80: "pole", 81: "traffic-sign", 99: "other-object",
    252: "moving-car", 253: "moving-bicyclist", 254: "moving-person",
    255: "moving-motorcyclist", 256: "moving-on-rails", 257: "moving-bus",
    258: "moving-truck", 259: "moving-other-vehicle",
}  # fmt: skip


# --- sequence files -------------------------------------------------------------------------


def read_calib(path: PathLike) -> Dict[str, np.ndarray]:
    """``KEY: v1 v2 ...`` lines -> flat float arrays (non-numeric lines are skipped)."""
    out = {}
    for line in Path(path).read_text().splitlines():
        key, _, values = line.partition(":")
        try:
            out[key.strip()] = np.array([float(v) for v in values.split()])
        except ValueError:
            continue
    return out


def _velo_to_cam(calib: Dict[str, np.ndarray]) -> np.ndarray:
    return np.vstack([calib["Tr"].reshape(3, 4), [0, 0, 0, 1]])


def sequence_ego_poses(seq_dir: PathLike, count: int) -> Optional[np.ndarray]:
    """
    ``scene_from_velo`` per frame from ``poses.txt`` (cam0 poses) and ``calib.txt`` (``Tr``), with
    the scene = world translated to the first frame; ``None`` when either file is missing.
    """
    seq_dir = Path(seq_dir)
    if not (seq_dir / "poses.txt").exists() or not (seq_dir / "calib.txt").exists():
        return None
    tr = _velo_to_cam(read_calib(seq_dir / "calib.txt"))
    world = g.invert(tr) @ load_poses(seq_dir / "poses.txt")[:count] @ tr
    return world_to_scene(world) @ world


def sequence_timestamps(seq_dir: PathLike, count: int, fps: float = 10) -> List[float]:
    """Seconds from the first frame (``times.txt``, else ``i / fps``)."""
    times = Path(seq_dir) / "times.txt"
    if not times.exists():
        return [i / fps for i in range(count)]
    t = [float(v) for v in times.read_text().split()][:count]
    return [v - t[0] for v in t]


def build_kitti_odometry(
    sequence_dir: PathLike,
    output: PathLike,
    world: bool = True,
    image_scale: float = 0.5,
) -> Path:
    """
    KITTI odometry / SemanticKITTI sequence -> ``semantickitti_<seq>.lidar.zip``.

    World frame (``world_from_velo = inv(Tr) @ pose_cam0 @ Tr``, translated to the first frame)
    when ``world`` and ``poses.txt`` + ``calib.txt`` exist, else the velodyne frame. ``image_2``
    frames are added when ``calib.txt`` has ``P2``. Every point is kept in file order.
    """
    seq = Path(sequence_dir)
    files = cloud_files(seq / "velodyne")
    if not files:
        raise ValueError(f"No velodyne/*.bin files in {seq}")
    ego = sequence_ego_poses(seq, len(files)) if world else None
    times = sequence_timestamps(seq, len(files))
    calib = read_calib(seq / "calib.txt") if (seq / "calib.txt").exists() else {}
    camera = None
    if "P2" in calib and "Tr" in calib and (seq / "image_2").is_dir():
        k, cam_from_cam0 = g.split_projection(calib["P2"].reshape(3, 4))
        camera = k, cam_from_cam0 @ _velo_to_cam(calib)

    def frames():
        for i, f in enumerate(files):
            cloud = read_bin(f)
            pose = None if ego is None else ego[i]
            xyz = cloud.xyz if pose is None else g.transform_points(pose, cloud.xyz)
            images = {}
            image = seq / "image_2" / f"{f.stem}.png"
            if camera is not None and image.exists():
                k, cfw = camera
                cfw = cfw if pose is None else cfw @ g.invert(pose)
                images["image_2"] = CameraImage(
                    image, None, k, cfw, {"model": "pinhole"}
                )
            yield Frame(xyz, cloud.intensity, times[i], pose, images)

    name = f"semantickitti_{seq.name}"
    return write_scene(
        package_path(output, name),
        frames(),
        name=name,
        coordinate_frame="sensor" if ego is None else "world",
        image_scale=image_scale,
    )


# --- labels -> Darwin -----------------------------------------------------------------------


def label_files(labels_dir: PathLike) -> List[Path]:
    return natsorted(Path(labels_dir).glob("*.label"), key=lambda p: p.name)


def parse_semantic_kitti(
    labels_dir: PathLike,
    item_name: Optional[str] = None,
    class_names: Optional[Dict[int, str]] = None,
    skip_ids: Sequence[int] = (0,),
) -> List[dt.AnnotationFile]:
    """
    ``sequences/<seq>/labels`` -> one ``AnnotationFile`` for ``semantickitti_<seq>.lidar.zip``.

    Frame ``i`` is the i-th ``.label`` file (natural sort). One ``point_mask_3d`` annotation per
    (class, instance > 0) with ``instance_id`` = instance, and one per class for instance 0.
    Unknown ids are named ``class_<id>``; ids in ``skip_ids`` are not imported.
    """
    labels_dir = Path(labels_dir)
    names = CLASS_NAMES if class_names is None else class_names
    files = label_files(labels_dir)
    tracks: Dict[tuple, Dict[int, dict]] = {}
    for frame, path in enumerate(files):
        labels = np.fromfile(path, dtype="<u4")
        values, inverse, counts = np.unique(
            labels, return_inverse=True, return_counts=True
        )
        order = np.argsort(inverse, kind="stable")
        for value, idx in zip(values, np.split(order, np.cumsum(counts)[:-1])):
            semantic, instance = int(value) & 0xFFFF, int(value) >> 16
            if semantic in skip_ids:
                continue
            ranges = indices_to_ranges(idx)
            tracks.setdefault((semantic, instance), {})[frame] = {
                "point_count": int(len(labels)),
                "ranges": ranges,
            }
    annotations = [
        make_track(
            names.get(semantic, f"class_{semantic}"),
            "point_mask_3d",
            frames,
            instance_id=instance or None,
        )
        for (semantic, instance), frames in sorted(tracks.items())
    ]
    seq = labels_dir.parent
    ego = sequence_ego_poses(seq, len(files))
    return [
        make_lidar_file(
            item_name or f"semantickitti_{seq.name}.lidar.zip",
            annotations,
            len(files),
            "sensor" if ego is None else "world",
            ego_poses=ego,
            timestamps=sequence_timestamps(seq, len(files)),
        )
    ]


# --- Darwin -> labels -----------------------------------------------------------------------


def export_semantic_kitti(
    annotation_files: Iterable[dt.AnnotationFile],
    output_dir: PathLike,
    class_ids: Optional[Dict[str, int]] = None,
) -> None:
    """
    Darwin ``point_mask_3d`` annotations -> ``<output>/<item stem>/labels/<frame:06d>.label``
    (``semantic | instance << 16``; instance from ``instance_id``, else 0). Class names map to ids
    with ``class_ids`` (default: SemanticKITTI names, ``class_<id>``, then new ids from 260); the
    mapping used is written to ``<output>/class_ids.json``. Overlapping masks: the later wins.
    Frames without any point mask are not written (their point count is unknown).
    """
    output_dir = Path(output_dir)
    ids = (
        {v: k for k, v in CLASS_NAMES.items()} if class_ids is None else dict(class_ids)
    )
    used: Dict[str, int] = {}

    def class_id(name: str) -> int:
        if name not in ids:
            m = re.fullmatch(r"class_(\d+)", name)
            ids[name] = int(m.group(1)) if m else max([259, *ids.values()]) + 1
        used[name] = ids[name]
        return ids[name]

    for af in annotation_files:
        out = output_dir / Path(af.filename).name.split(".")[0] / "labels"
        for frame, objects in frame_objects(af, ("point_mask_3d",)).items():
            labels = np.zeros(max(o.data["point_count"] for o in objects), "<u4")
            for o in objects:
                value = class_id(o.annotation.annotation_class.name) | (
                    (o.instance_id or 0) << 16
                )
                labels[ranges_to_indices(o.data["ranges"])] = value
            out.mkdir(parents=True, exist_ok=True)
            labels.tofile(out / f"{frame:06d}.label")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "class_ids.json").write_text(json.dumps(used, indent=1))
