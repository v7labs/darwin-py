"""
ASAM OpenLABEL 1.0 <-> Darwin 3D annotations.

Geometry: ``cuboid`` (10 values ``x y z qx qy qz qw sx sy sz``, scalar-last quaternion, or 9
values ``x y z rx ry rz sx sy sz`` with ``R = Rz(rz) Ry(ry) Rx(rx)``) <-> ``cuboid_3d``
(``sx/sy/sz`` = length/width/height); ``poly3d`` (``closed``) <-> ``polygon_3d`` /
``polyline_3d``; ``point3d`` <-> ``keypoint_3d``. Coordinate systems follow the OpenLABEL / VCD
convention: ``pose_wrt_parent`` maps child -> parent points, ``transform_src_to_dst`` maps
src -> dst points, per-frame ``frame_properties.transforms`` override the static poses.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

import darwin.datatypes as dt
from darwin.lidar import geometry as g
from darwin.lidar.darwin_json import (
    frame_objects,
    item_stem,
    make_lidar_file,
    make_track,
    pointcloud_slot,
)

logger = logging.getLogger(__name__)

GEOMETRY = ("cuboid", "poly3d", "point3d")
NON_GEOMETRY = ("num", "text", "boolean", "vec")


def is_openlabel(path: dt.PathLike) -> bool:
    """True for a ``.json`` file whose root key is ``openlabel`` (reads only its first bytes)."""
    path = Path(path)
    if not path.is_file() or path.suffix.lower() != ".json":
        return False
    with path.open("rb") as f:
        return re.match(rb'\s*\{\s*"openlabel"\s*:', f.read(256)) is not None


def _matrix(t: Dict[str, Any]) -> np.ndarray:
    if "matrix4x4" in t:
        return np.asarray(t["matrix4x4"], float).reshape(4, 4)
    translation = t.get("translation", [0, 0, 0])
    if "quaternion" in t:
        qx, qy, qz, qw = t["quaternion"]
        return g.make_pose(g.quat_to_rot(qw, qx, qy, qz), translation)
    if "euler_angles" in t and t.get("sequence", "ZYX") == "ZYX":
        rz, ry, rx = t["euler_angles"]
        return g.make_pose(g.euler_to_rot(rx, ry, rz), translation)
    raise ValueError(f"Unsupported OpenLABEL transform: {sorted(t)}")


def _xyz(v: Iterable[float]) -> Dict[str, float]:
    x, y, z = v
    return {"x": float(x), "y": float(y), "z": float(z)}


class _Poses:
    """``target_from_<coordinate system>`` per frame."""

    def __init__(self, root: Dict[str, Any], target: Optional[str]):
        self.cs: Dict[str, Any] = root.get("coordinate_systems") or {}
        self.frames: Dict[str, Any] = root.get("frames") or {}
        roots = [n for n, c in self.cs.items() if not c.get("parent")]
        self.target = target or (roots[0] if roots else None)
        if self.target is not None and self.target not in self.cs:
            raise ValueError(f"Unknown coordinate system '{self.target}'")

    def transforms(self, f: int) -> Dict[str, Any]:
        frame = self.frames.get(str(f)) or {}
        return (frame.get("frame_properties") or {}).get("transforms") or {}

    def _root_from(self, name: str, f: int) -> Tuple[np.ndarray, str]:
        m = np.eye(4)
        for _ in range(len(self.cs) + 1):
            parent = self.cs[name].get("parent")
            if not parent:
                return m, name
            edge = None
            for t in self.transforms(f).values():
                if (t.get("src"), t.get("dst")) == (name, parent):
                    edge = _matrix(t["transform_src_to_dst"])
                elif (t.get("src"), t.get("dst")) == (parent, name):
                    edge = np.linalg.inv(_matrix(t["transform_src_to_dst"]))
            if edge is None:
                pose = self.cs[name].get("pose_wrt_parent")
                edge = _matrix(pose) if pose else np.eye(4)
            m, name = edge @ m, parent
        raise ValueError("Cycle in OpenLABEL coordinate_systems")

    def target_from(self, name: Optional[str], f: int) -> np.ndarray:
        if name is None or name == self.target or self.target is None:
            return np.eye(4)
        if name not in self.cs:
            raise ValueError(f"Unknown coordinate system '{name}'")
        src, src_root = self._root_from(name, f)
        dst, dst_root = self._root_from(self.target, f)
        if src_root != dst_root:
            raise ValueError(f"'{name}' and '{self.target}' are not connected")
        return np.linalg.inv(dst) @ src


def _convert(
    kind: str, geom: Dict[str, Any], pose: np.ndarray
) -> Tuple[str, Dict[str, Any]]:
    v = [float(x) for x in geom["val"]]
    if kind == "cuboid":
        if len(v) == 10:
            r = g.quat_to_rot(v[6], v[3], v[4], v[5])
        elif len(v) == 9:
            r = g.euler_to_rot(v[3], v[4], v[5])
        else:
            raise ValueError(f"OpenLABEL cuboid needs 9 or 10 values, got {len(v)}")
        return "cuboid_3d", g.pose_to_cuboid(pose @ g.make_pose(r, v[:3]), v[-3:])
    pts = g.transform_points(pose, np.asarray(v).reshape(-1, 3))
    if kind == "poly3d":
        kind_3d = "polygon_3d" if geom.get("closed") else "polyline_3d"
        return kind_3d, {"path": [_xyz(p) for p in pts]}
    return "keypoint_3d", _xyz(pts[0])


def _geometries(
    object_data: Dict[str, Any], warned: set
) -> Iterable[Tuple[str, int, Dict]]:
    for kind, geoms in (object_data or {}).items():
        if kind in GEOMETRY:
            for k, geom in enumerate(geoms):
                yield kind, k, geom
        elif kind not in NON_GEOMETRY and kind not in warned:
            warned.add(kind)
            logger.warning(
                f"OpenLABEL '{kind}' object data has no 3D Darwin type, skipped"
            )


def parse_openlabel(
    path: dt.PathLike,
    item_name: Optional[str] = None,
    target_frame: Optional[str] = None,
) -> List[dt.AnnotationFile]:
    """
    One OpenLABEL file -> one ``AnnotationFile`` (a Darwin track per object geometry, class =
    object ``type``, ``instance_id`` = 1-based object order), geometry in ``target_frame``
    (default: the root coordinate system). Items whose frames carry per-frame transforms are
    ``world`` items with ``ego_pose`` = ``target_from_<moving frame>``, others ``sensor`` items.
    Object-level (static) data that stays fixed in the target frame becomes one keyframe per
    ``frame_intervals`` entry; otherwise it is expanded to every frame of the intervals.
    """
    path = Path(path)
    root = json.loads(path.read_text())["openlabel"]
    poses = _Poses(root, target_frame)
    objects: Dict[str, Any] = root.get("objects") or {}
    frame_keys = [int(f) for f in (root.get("frames") or {})]
    ends = [i["frame_end"] for i in root.get("frame_intervals") or []]
    ends += [
        i["frame_end"] for o in objects.values() for i in o.get("frame_intervals") or []
    ]
    frame_count = max(frame_keys + ends + [0]) + 1
    warned: set = set()

    tracks: Dict[Tuple, Dict[int, Dict[str, Any]]] = {}
    for f in sorted(frame_keys):
        frame_objs = (root["frames"][str(f)] or {}).get("objects") or {}
        for oid, fo in frame_objs.items():
            for kind, k, geom in _geometries(fo.get("object_data"), warned):
                pose = poses.target_from(geom.get("coordinate_system"), f)
                t, data = _convert(kind, geom, pose)
                tracks.setdefault((oid, kind, geom.get("name", k), t), {})[f] = data

    static: Dict[Tuple, List[List[int]]] = {}
    for oid, obj in objects.items():
        intervals = [
            [i["frame_start"], i["frame_end"] + 1]
            for i in obj.get("frame_intervals") or []
        ] or [[0, frame_count]]
        frames = [f for s, e in intervals for f in range(s, e)]
        for kind, k, geom in _geometries(obj.get("object_data"), warned):
            cs = geom.get("coordinate_system")
            per_frame = [poses.target_from(cs, f) for f in frames]
            t, _ = _convert(kind, geom, per_frame[0])
            key = (oid, kind, geom.get("name", k), t)
            fixed = all(np.allclose(p, per_frame[0]) for p in per_frame)
            if fixed and key not in tracks:
                tracks[key] = {
                    s: _convert(kind, geom, per_frame[0])[1] for s, _ in intervals
                }
                static[key] = intervals
            else:
                for f, p in zip(frames, per_frame):
                    tracks.setdefault(key, {}).setdefault(f, _convert(kind, geom, p)[1])

    order = {oid: n for n, oid in enumerate(objects)}
    annotations = []
    for key in sorted(tracks, key=lambda k: (order.get(k[0], len(order)), str(k[0]))):
        oid, _, _, t = key
        cls = (objects.get(oid) or {}).get("type") or "object"
        track = make_track(
            cls, t, tracks[key], instance_id=order.get(oid, len(order)) + 1
        )
        if key in static:
            track.segments = static[key]
            track.interpolated = True
        annotations.append(track)

    timestamps = []
    for f in range(frame_count):
        props = ((root.get("frames") or {}).get(str(f)) or {}).get(
            "frame_properties"
        ) or {}
        ts = props.get("timestamp")
        timestamps.append(float(ts) if isinstance(ts, (int, float)) else f / 10)

    cameras = {
        n for n, st in (root.get("streams") or {}).items() if st.get("type") == "camera"
    }
    moving = next(
        (
            t
            for f in range(frame_count)
            for t in poses.transforms(f).values()
            if not {t.get("src"), t.get("dst")} & cameras
        ),
        None,
    )
    ego_poses = None
    if moving is not None:
        ego_cs = moving["src"] if moving["src"] != poses.target else moving["dst"]
        ego_poses = [poses.target_from(ego_cs, f) for f in range(frame_count)]

    if item_name is None:
        meta = root.get("metadata") or {}
        uri = next(
            (
                s.get("uri")
                for s in (root.get("streams") or {}).values()
                if s.get("uri")
            ),
            None,
        )
        named = meta.get("tagged_file") or meta.get("file") or uri
        stem = (
            path.name[: -len(".openlabel.json")]
            if path.name.endswith(".openlabel.json")
            else path.stem
        )
        item_name = Path(named).name if named else f"{stem}.lidar.zip"

    return [
        make_lidar_file(
            item_name,
            annotations,
            frame_count,
            coordinate_frame="world" if ego_poses is not None else "sensor",
            ego_poses=ego_poses,
            timestamps=timestamps,
        )
    ]


# --- export ---------------------------------------------------------------------------------


def _geometry_json(
    annotation_type: str, data: Dict[str, Any], cs: str
) -> Tuple[str, Dict]:
    if annotation_type == "cuboid_3d":
        pose = g.cuboid_to_pose(data)
        qw, qx, qy, qz = g.rot_to_quat(pose)
        d = data["dimensions"]
        val = [*pose[:3, 3].tolist(), qx, qy, qz, qw, d["x"], d["y"], d["z"]]
        return "cuboid", {"name": "shape", "val": val, "coordinate_system": cs}
    if annotation_type in ("polyline_3d", "polygon_3d"):
        val = [float(p[k]) for p in data["path"] for k in "xyz"]
        closed = annotation_type == "polygon_3d"
        return "poly3d", {
            "name": "shape",
            "val": val,
            "closed": closed,
            "coordinate_system": cs,
        }
    val = [float(data[k]) for k in "xyz"]
    return "point3d", {"name": "shape", "val": val, "coordinate_system": cs}


def _camera_stream(cam: Dict[str, Any]) -> Dict[str, Any]:
    """OpenLABEL camera stream: ``intrinsics_pinhole`` (pinhole / opencv) or ``intrinsics_fisheye``."""
    k = g.intrinsics_matrix(cam)
    dist = cam.get("distortion") or {"model": "pinhole"}
    c = [float(v) for v in dist.get("coefficients") or []]
    size = {"width_px": cam.get("width"), "height_px": cam.get("height")}
    if dist["model"] == "fisheye":
        props = {
            "intrinsics_fisheye": {
                **size,
                "lens_coeffs_1x4": c,
                "center_x": k[0, 2],
                "center_y": k[1, 2],
                "focal_length_x": k[0, 0],
                "focal_length_y": k[1, 1],
            }
        }
    else:
        pinhole = {**size, "camera_matrix_3x4": np.c_[k, np.zeros(3)].ravel().tolist()}
        if dist["model"] == "opencv":
            pinhole["distortion_coeffs_1xN"] = c + [0.0] * (5 - len(c))
        props = {"intrinsics_pinhole": pinhole}
    return {"type": "camera", "stream_properties": props}


def to_openlabel(annotation_file: dt.AnnotationFile) -> Dict[str, Any]:
    """
    OpenLABEL JSON of one ``pointcloud`` item (point masks have no OpenLABEL type: skipped).
    Calibrated cameras of the export become camera streams with a coordinate system each (child
    of ``ego``, or of ``sensor`` for sensor-frame items) and a per-frame ``<camera>_to_<parent>``
    transform.
    """
    slot = pointcloud_slot(annotation_file)
    meta = (slot.metadata if slot else None) or {}
    meta_frames = meta.get("frames") or []
    world = meta.get("coordinate_frame") == "world"
    objects_by_frame = frame_objects(annotation_file)
    count = max(
        [(slot.frame_count if slot else None) or 0, len(meta_frames), 1]
        + [f + 1 for f in objects_by_frame]
    )
    cs = "scene" if world else "sensor"
    coordinate_systems = (
        {
            "scene": {"type": "scene_cs", "parent": "", "children": ["ego"]},
            "ego": {"type": "local_cs", "parent": "scene", "children": []},
        }
        if world
        else {"sensor": {"type": "sensor_cs", "parent": "", "children": []}}
    )
    streams: Dict[str, Any] = {"lidar": {"type": "lidar"}}
    parent = "ego" if world else "sensor"
    cameras = {
        n: c
        for n, c in g.slot_cameras(meta).items()
        if g.intrinsics_matrix(c) is not None
    }
    for name, cam in cameras.items():
        streams[name] = _camera_stream(cam)
        coordinate_systems[name] = {
            "type": "sensor_cs",
            "parent": parent,
            "children": [],
        }
        coordinate_systems[parent]["children"].append(name)
    frames: Dict[str, Any] = {}
    for i in range(count):
        props: Dict[str, Any] = {}
        if i < len(meta_frames) and meta_frames[i].get("timestamp") is not None:
            props["timestamp"] = meta_frames[i]["timestamp"]
        pose = g.ego_pose_of(meta, i)
        transforms = {}
        if pose is not None:
            transforms["ego_to_scene"] = {
                "src": "ego",
                "dst": "scene",
                "transform_src_to_dst": {"matrix4x4": pose.ravel().tolist()},
            }
        for name in cameras:
            cfw = g.camera_from_world_of(meta, i, name)
            if cfw is not None:
                transforms[f"{name}_to_{parent}"] = {
                    "src": name,
                    "dst": parent,
                    "transform_src_to_dst": {
                        "matrix4x4": g.invert(cfw if pose is None else cfw @ pose)
                        .ravel()
                        .tolist()
                    },
                }
        if transforms:
            props["transforms"] = transforms
        frames[str(i)] = {"objects": {}, "frame_properties": props}

    objects: Dict[str, Any] = {}
    oids: Dict[int, str] = {}
    skipped = 0
    for annotation in annotation_file.annotations:
        t = annotation.annotation_class.annotation_type
        if t == "point_mask_3d":
            skipped += 1
            continue
        if t not in dt.LIDAR_ANNOTATION_TYPES:
            continue
        oid = oids[id(annotation)] = str(len(objects))
        segments = getattr(annotation, "segments", None) or [[0, 1]]
        objects[oid] = {
            "name": annotation.id or f"{annotation.annotation_class.name}_{oid}",
            "type": annotation.annotation_class.name,
            "frame_intervals": [
                {"frame_start": s, "frame_end": e - 1} for s, e in segments
            ],
        }
        frames_of = getattr(annotation, "frames", {0: annotation})
        if len(frames_of) == 1 and sum(e - s for s, e in segments) > 1:
            # one keyframe over a longer range: constant geometry, stored once on the object
            kind, geom = _geometry_json(t, next(iter(frames_of.values())).data, cs)
            objects[oid]["object_data"] = {kind: [geom]}
    if skipped:
        logger.warning(
            f"{annotation_file.filename}: {skipped} point_mask_3d annotations skipped"
        )

    for f, objs in objects_by_frame.items():
        for o in objs:
            oid = oids.get(id(o.annotation))
            if oid is None or "object_data" in objects[oid]:
                continue
            kind, geom = _geometry_json(o.annotation_type, o.data, cs)
            frame = frames.setdefault(str(f), {"objects": {}, "frame_properties": {}})
            od = frame["objects"].setdefault(oid, {"object_data": {}})["object_data"]
            od.setdefault(kind, []).append(geom)

    return {
        "openlabel": {
            "metadata": {
                "schema_version": "1.0.0",
                "tagged_file": annotation_file.filename,
            },
            "coordinate_systems": coordinate_systems,
            "streams": streams,
            "objects": objects,
            "frames": frames,
            "frame_intervals": [{"frame_start": 0, "frame_end": count - 1}],
        }
    }


def export_openlabel(
    annotation_files: Iterable[dt.AnnotationFile], output_dir: dt.PathLike
) -> List[Path]:
    """Writes ``<item stem>.openlabel.json`` per ``pointcloud`` item."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for af in annotation_files:
        if pointcloud_slot(af) is None:
            continue
        path = out / f"{item_stem(af.filename)}.openlabel.json"
        path.write_text(json.dumps(to_openlabel(af)))
        paths.append(path)
    return paths
