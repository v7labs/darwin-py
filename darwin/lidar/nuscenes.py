"""
nuScenes (devkit-free): scene packages, ``sample_annotation`` boxes, lidarseg / panoptic point
masks, and a ``sample_annotation``-like export.

Tables are read from ``<dataroot>/<version>/*.json``. Only key-frame samples are used (2 Hz, the
frames that carry labels). The scene frame is the global frame translated so the first sample's
LIDAR_TOP ego position is the origin; ``ego_pose`` is ``scene_from_ego`` (nuScenes ego frame).
"""

import json
import uuid
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

import darwin.datatypes as dt
from darwin.lidar import geometry as g
from darwin.lidar.darwin_json import (
    frame_objects,
    item_stem,
    make_lidar_file,
    make_track,
    mask_to_ranges,
    pointcloud_slot,
)
from darwin.lidar.pointcloud import PathLike, read_bin
from darwin.lidar.scene import CameraImage, Frame, package_path, write_scene

CAMERAS = (
    "CAM_FRONT",
    "CAM_FRONT_RIGHT",
    "CAM_FRONT_LEFT",
    "CAM_BACK",
    "CAM_BACK_LEFT",
    "CAM_BACK_RIGHT",
)
FPS = 2


class _Tables:
    """nuScenes tables by token, loaded on first use."""

    def __init__(self, version_dir: PathLike):
        self.dir = Path(version_dir)
        self._tables: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def __getitem__(self, name: str) -> Dict[str, Dict[str, Any]]:
        if name not in self._tables:
            path = self.dir / f"{name}.json"
            rows = json.loads(path.read_text()) if path.exists() else []
            self._tables[name] = {r["token"]: r for r in rows}
        return self._tables[name]

    @cached_property
    def keyframes(self) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """``(sample_token, channel) -> sample_data`` of key frames."""
        calib, sensor = self["calibrated_sensor"], self["sensor"]
        return {
            (
                sd["sample_token"],
                sensor[calib[sd["calibrated_sensor_token"]]["sensor_token"]]["channel"],
            ): sd
            for sd in self["sample_data"].values()
            if sd.get("is_key_frame")
        }

    def scene(self, scene: str) -> Dict[str, Any]:
        for rec in self["scene"].values():
            if scene in (rec["token"], rec["name"]):
                return rec
        raise ValueError(f"No scene '{scene}' in {self.dir}")

    def pose(self, table: str, token: str) -> np.ndarray:
        r = self[table][token]
        return g.make_pose(g.quat_to_rot(*r["rotation"]), r["translation"])


def _frames(
    t: _Tables, scene: Dict[str, Any]
) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
    """``(sample, LIDAR_TOP sample_data)`` per key frame, in time order."""
    out, token = [], scene["first_sample_token"]
    while token:
        sample = t["sample"][token]
        out.append((sample, t.keyframes[(token, "LIDAR_TOP")]))
        token = sample["next"]
    return out


def _scene_geometry(
    t: _Tables, frames: Sequence[Tuple[dict, dict]]
) -> Tuple[np.ndarray, np.ndarray, List[float]]:
    """``scene_from_global``, ``scene_from_ego`` per frame and timestamps (seconds from the first)."""
    global_from_ego = np.array(
        [t.pose("ego_pose", sd["ego_pose_token"]) for _, sd in frames]
    )
    scene_from_global = g.translation(-global_from_ego[0, :3, 3])
    t0 = frames[0][1]["timestamp"]
    return (
        scene_from_global,
        scene_from_global @ global_from_ego,
        [(sd["timestamp"] - t0) / 1e6 for _, sd in frames],
    )


def _item_name(scene: Dict[str, Any]) -> str:
    return f"{scene['name']}.lidar.zip"


def _uuid(token: str) -> str:
    try:
        return str(uuid.UUID(hex=token))
    except ValueError:
        return str(uuid.uuid5(uuid.NAMESPACE_OID, token))


def _scenes(t: _Tables, scenes: Optional[Iterable[str]]) -> List[Dict[str, Any]]:
    return (
        [t.scene(s) for s in scenes]
        if scenes is not None
        else list(t["scene"].values())
    )


def build_nuscenes(
    dataroot: PathLike,
    scene: str,
    output: PathLike,
    version: str = "v1.0-mini",
    cameras: Optional[Sequence[str]] = None,
    image_scale: float = 0.5,
) -> Path:
    """One nuScenes scene (name or token) -> ``<scene name>.lidar.zip`` (world frame, 2 Hz)."""
    dataroot = Path(dataroot)
    t = _Tables(dataroot / version)
    rec = t.scene(scene)
    frames = _frames(t, rec)
    scene_from_global, ego, timestamps = _scene_geometry(t, frames)
    global_from_scene = g.invert(scene_from_global)

    def gen():
        for i, (sample, sd) in enumerate(frames):
            cloud = read_bin(dataroot / sd["filename"], 5)
            scene_from_lidar = ego[i] @ t.pose(
                "calibrated_sensor", sd["calibrated_sensor_token"]
            )
            images = {}
            for cam in cameras or CAMERAS:
                csd = t.keyframes.get((sample["token"], cam))
                if csd is None:
                    continue
                calib = t["calibrated_sensor"][csd["calibrated_sensor_token"]]
                cam_from_scene = (
                    g.invert(t.pose("calibrated_sensor", calib["token"]))
                    @ g.invert(t.pose("ego_pose", csd["ego_pose_token"]))
                    @ global_from_scene
                )
                # released nuScenes images are undistorted
                images[cam] = CameraImage(
                    dataroot / csd["filename"],
                    None,
                    np.asarray(calib["camera_intrinsic"], float),
                    cam_from_scene,
                    {"model": "pinhole"},
                )
            yield Frame(
                g.transform_points(scene_from_lidar, cloud.xyz),
                cloud.intensity,
                timestamps[i],
                ego[i],
                images,
            )

    return write_scene(
        package_path(output, rec["name"]),
        gen(),
        name=rec["name"],
        fps=FPS,
        coordinate_frame="world",
        image_scale=image_scale,
        origin=global_from_scene[:3, 3],
    )


def parse_nuscenes(
    version_dir: PathLike, scenes: Optional[Iterable[str]] = None
) -> List[dt.AnnotationFile]:
    """
    ``sample_annotation`` -> ``cuboid_3d`` tracks (one per instance) in the scene frame of
    :func:`build_nuscenes`, one ``AnnotationFile`` per scene.
    """
    t = _Tables(version_dir)
    by_sample: Dict[str, List[Dict[str, Any]]] = {}
    for a in t["sample_annotation"].values():
        by_sample.setdefault(a["sample_token"], []).append(a)
    out = []
    for rec in _scenes(t, scenes):
        frames = _frames(t, rec)
        scene_from_global, ego, timestamps = _scene_geometry(t, frames)
        tracks: Dict[str, Dict[str, Any]] = {}
        for i, (sample, _) in enumerate(frames):
            for a in by_sample.get(sample["token"], []):
                track = tracks.setdefault(
                    a["instance_token"], {"frames": {}, "attributes": {}}
                )
                w, length, h = a["size"]
                box = scene_from_global @ g.make_pose(
                    g.quat_to_rot(*a["rotation"]), a["translation"]
                )
                track["frames"][i] = g.pose_to_cuboid(box, (length, w, h))
                track["attributes"][i] = [
                    t["attribute"][k]["name"] for k in a.get("attribute_tokens", [])
                ]
        annotations = [
            make_track(
                t["category"][t["instance"][token]["category_token"]]["name"],
                "cuboid_3d",
                track["frames"],
                instance_id=n + 1,
                attributes=track["attributes"],
                annotation_id=_uuid(token),
            )
            for n, (token, track) in enumerate(tracks.items())
        ]
        out.append(
            make_lidar_file(
                _item_name(rec),
                annotations,
                len(frames),
                "world",
                np.round(ego, 6),
                timestamps,
                FPS,
            )
        )
    return out


def parse_nuscenes_lidarseg(
    version_dir: PathLike,
    scenes: Optional[Iterable[str]] = None,
    panoptic: bool = False,
    skip: Sequence[int] = (0,),
) -> List[dt.AnnotationFile]:
    """
    nuScenes-lidarseg (``uint8`` class per point) -> one ``point_mask_3d`` per class per scene;
    with ``panoptic`` (``uint16`` class * 1000 + instance) one per (class, instance > 0) with that
    ``instance_id``, and one per class for stuff (instance 0). Classes in ``skip`` are ignored.
    """
    version_dir = Path(version_dir)
    t = _Tables(version_dir)
    table = t["panoptic" if panoptic else "lidarseg"]
    by_sd = {r["sample_data_token"]: r["filename"] for r in table.values()}
    names = {c["index"]: c["name"] for c in t["category"].values() if "index" in c}
    out = []
    for rec in _scenes(t, scenes):
        frames = _frames(t, rec)
        _, ego, timestamps = _scene_geometry(t, frames)
        groups: Dict[Tuple[int, int], Dict[int, Dict[str, Any]]] = {}
        for i, (_, sd) in enumerate(frames):
            if sd["token"] not in by_sd:
                continue
            path = version_dir.parent / by_sd[sd["token"]]
            if panoptic:
                labels = np.load(path)["data"].astype(np.int64)
            else:
                labels = np.fromfile(path, np.uint8).astype(np.int64) * 1000
            for v in np.unique(labels):
                c, k = divmod(int(v), 1000)
                if c not in skip:
                    mask = {
                        "point_count": len(labels),
                        "ranges": mask_to_ranges(labels == v),
                    }
                    groups.setdefault((c, k), {})[i] = mask
        annotations = [
            make_track(names.get(c, str(c)), "point_mask_3d", f, instance_id=k or None)
            for (c, k), f in sorted(groups.items())
        ]
        out.append(
            make_lidar_file(
                _item_name(rec),
                annotations,
                len(frames),
                "world",
                np.round(ego, 6),
                timestamps,
                FPS,
            )
        )
    return out


def _token(*parts: Any) -> str:
    return uuid.uuid5(uuid.NAMESPACE_OID, ":".join(map(str, parts))).hex


def _calibrated_sensors(
    meta: Dict[str, Any], f: int, scene_from_ego: Optional[np.ndarray]
) -> List[Dict[str, Any]]:
    out = []
    for name, cam in g.slot_cameras(meta).items():
        k, cfw = g.intrinsics_matrix(cam), g.camera_from_world_of(meta, f, name)
        if k is None or cfw is None:
            continue
        ego_from_cam = g.invert(cfw if scene_from_ego is None else cfw @ scene_from_ego)
        rec = {
            "channel": name,
            "width": cam.get("width"),
            "height": cam.get("height"),
            "camera_intrinsic": k.tolist(),
            "translation": ego_from_cam[:3, 3].tolist(),
            "rotation": list(g.rot_to_quat(ego_from_cam)),
        }
        if cam.get("distortion"):
            rec["distortion"] = cam["distortion"]
        out.append(rec)
    return out


def export_nuscenes(
    annotation_files: Iterable[dt.AnnotationFile],
    output_dir: PathLike,
    origin: Optional[Sequence[float]] = None,
) -> List[Path]:
    """
    ``cuboid_3d`` annotations -> ``<output_dir>/<item stem>.json``:
    ``{"item", "coordinate_frame", "frames": [{"sample_index", "timestamp", "ego_pose"?,
    "calibrated_sensor"?, "sample_annotation": [...]}]}`` with nuScenes ``sample_annotation``
    fields (``size`` = ``[width, length, height]``, ``rotation`` = ``[w, x, y, z]``) in the global
    frame when the scene origin in global coordinates is known (``origin``, else the export's
    slot ``metadata.origin``), otherwise in the scene frame. ``calibrated_sensor``: one record per
    calibrated camera of the export (``channel``, ``width``, ``height``, ``camera_intrinsic``,
    ``distortion`` and ``translation`` / ``rotation`` = ``ego_from_camera`` at that frame's image;
    with the frame's ``ego_pose`` it maps the image exactly).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for af in annotation_files:
        slot = pointcloud_slot(af)
        if slot is None:
            continue
        meta = slot.metadata or {}
        shift = np.asarray(
            origin if origin is not None else meta.get("origin", (0.0, 0.0, 0.0)), float
        )
        meta_frames = meta.get("frames") or []
        objs = frame_objects(af, ("cuboid_3d",))
        count = max([slot.frame_count or 0, len(meta_frames), *[f + 1 for f in objs]])
        track_frames: Dict[int, List[int]] = {}
        for f, items in objs.items():
            for o in items:
                track_frames.setdefault(id(o.annotation), []).append(f)
        frames = []
        for f in range(count):
            frame: Dict[str, Any] = {"sample_index": f}
            if f < len(meta_frames) and "timestamp" in meta_frames[f]:
                frame["timestamp"] = meta_frames[f]["timestamp"]
            scene_from_ego = g.ego_pose_of(meta, f)
            if scene_from_ego is not None:
                pose = g.translation(shift) @ scene_from_ego
                frame["ego_pose"] = {
                    "translation": pose[:3, 3].tolist(),
                    "rotation": list(g.rot_to_quat(pose)),
                }
            sensors = _calibrated_sensors(meta, f, scene_from_ego)
            if sensors:
                frame["calibrated_sensor"] = sensors
            records = []
            for o in objs.get(f, []):
                a, d = o.annotation, o.data["dimensions"]
                key = a.id or f"{a.annotation_class.name}:{id(a)}"
                fs = track_frames[id(a)]
                k = fs.index(f)
                pose_box = g.cuboid_to_pose(o.data)
                records.append(
                    {
                        "token": _token(key, f),
                        "sample_index": f,
                        "timestamp": frame.get("timestamp"),
                        "instance_token": (
                            a.id.replace("-", "") if a.id else _token(key)
                        ),
                        "category_name": a.annotation_class.name,
                        "translation": (pose_box[:3, 3] + shift).tolist(),
                        "size": [d["y"], d["x"], d["z"]],
                        "rotation": list(g.rot_to_quat(pose_box)),
                        "attribute_names": o.attributes,
                        "prev": _token(key, fs[k - 1]) if k > 0 else "",
                        "next": _token(key, fs[k + 1]) if k + 1 < len(fs) else "",
                    }
                )
            frame["sample_annotation"] = records
            frames.append(frame)
        path = output_dir / f"{item_stem(af.filename)}.json"
        path.write_text(
            json.dumps(
                {
                    "item": af.filename,
                    "coordinate_frame": meta.get("coordinate_frame"),
                    "frames": frames,
                }
            )
        )
        paths.append(path)
    return paths
