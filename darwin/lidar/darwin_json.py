"""
Darwin JSON 2.0 for ``pointcloud`` items: building annotation files from dataset labels,
serializing them, and iterating their per-frame 3D geometry (for exporters).
"""

import base64
import json
import uuid
import zlib
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Sequence

import numpy as np

import darwin.datatypes as dt


SLOT_NAME = "0"
SCHEMA_REF = (
    "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json"
)


def item_stem(name: str) -> str:
    """``scene.lidar.zip`` -> ``scene``, ``cloud.pcd`` -> ``cloud``."""
    name = Path(name).name
    return (
        name[: -len(".lidar.zip")] if name.endswith(".lidar.zip") else Path(name).stem
    )


def indices_to_ranges(indices: np.ndarray) -> List[int]:
    """Sorted unique point indices -> ``point_mask_3d`` ``ranges`` (flat ``[start, length, ...]``)."""
    idx = np.asarray(indices, np.int64)
    if not len(idx):
        return []
    breaks = np.flatnonzero(np.diff(idx) != 1)
    starts = idx[np.r_[0, breaks + 1]]
    lengths = idx[np.r_[breaks, len(idx) - 1]] - starts + 1
    return np.stack([starts, lengths], 1).ravel().tolist()


def mask_to_ranges(mask: np.ndarray) -> List[int]:
    """Boolean per-point mask -> ``point_mask_3d`` ``ranges``."""
    return indices_to_ranges(np.flatnonzero(mask))


def ranges_to_indices(ranges: Sequence[int]) -> np.ndarray:
    """``point_mask_3d`` ``ranges`` -> point indices."""
    r = np.asarray(ranges, np.int64).reshape(-1, 2)
    starts, lengths = r[:, 0], r[:, 1]
    offsets = np.repeat(np.cumsum(lengths) - lengths, lengths)
    return np.arange(lengths.sum()) - offsets + np.repeat(starts, lengths)


def pack_ranges(ranges: Sequence[int]) -> str:
    """
    ``ranges`` -> ``packed_ranges``: base64 of zlib-compressed unsigned LEB128 varints
    ``gap, length, ...``, each gap counted from the end of the previous run (the first from 0).
    """
    # ponytail: Python loops, ~1 s per million runs; vectorize if huge masks get common
    out, end = bytearray(), 0
    for start, length in zip(ranges[::2], ranges[1::2]):
        for v in (int(start) - end, int(length)):
            while v >= 0x80:
                out.append(v & 0x7F | 0x80)
                v >>= 7
            out.append(v)
        end = int(start) + int(length)
    return base64.b64encode(zlib.compress(bytes(out))).decode("ascii")


def unpack_ranges(packed: str) -> List[int]:
    """``packed_ranges`` -> ``ranges`` (inverse of :func:`pack_ranges`)."""
    values, value, shift = [], 0, 0
    for byte in zlib.decompress(base64.b64decode(packed, validate=True)):
        value |= (byte & 0x7F) << shift
        if byte & 0x80:
            shift += 7
        else:
            values.append(value)
            value, shift = 0, 0
    if shift or len(values) % 2:
        raise ValueError("packed_ranges: truncated varints")
    out, end = [], 0
    for gap, length in zip(values[::2], values[1::2]):
        out += [end + gap, length]
        end += gap + length
    return out


def unpack_point_mask(data: Dict[str, Any]) -> Dict[str, Any]:
    """A ``point_mask_3d`` with ``packed_ranges`` -> the same mask with plain ``ranges``."""
    if "packed_ranges" not in data:
        return data
    out = {k: v for k, v in data.items() if k != "packed_ranges"}
    out["ranges"] = unpack_ranges(data["packed_ranges"])
    return out


def pack_point_mask(data: Dict[str, Any], min_runs: int = 64) -> Dict[str, Any]:
    """``packed_ranges`` form of a ``point_mask_3d`` when it has many runs and packs smaller."""
    ranges = data.get("ranges")
    if ranges is None or len(ranges) < 2 * min_runs:
        return data
    packed = pack_ranges(ranges)
    if len(packed) >= len(json.dumps(ranges)):
        return data
    out = {k: v for k, v in data.items() if k != "ranges"}
    out["packed_ranges"] = packed
    return out


def segments_of(frames: Iterable[int]) -> List[List[int]]:
    """Contiguous runs of frame indices as Darwin ``ranges`` (``[start, end)``)."""
    out: List[List[int]] = []
    for f in sorted(set(frames)):
        if out and out[-1][1] == f:
            out[-1][1] = f + 1
        else:
            out.append([f, f + 1])
    return out


def make_track(
    class_name: str,
    annotation_type: str,
    frames: Dict[int, Dict[str, Any]],
    instance_id: Optional[int] = None,
    attributes: Optional[Dict[int, List[str]]] = None,
    interpolated: Optional[bool] = None,
    annotation_id: Optional[str] = None,
) -> dt.VideoAnnotation:
    """
    One Darwin annotation over several frames (every given frame is a keyframe; gaps split the
    ranges). ``instance_id`` is written on every frame, ``attributes`` per frame.
    Point masks are never interpolated.
    """
    if not frames:
        raise ValueError("A track needs at least one frame")
    per_frame = {}
    for f, data in sorted(frames.items()):
        subs = []
        if instance_id is not None:
            subs.append(dt.make_instance_id(int(instance_id)))
        if attributes and attributes.get(f):
            subs.append(dt.make_attributes(list(attributes[f])))
        per_frame[int(f)] = dt.make_lidar_annotation(
            class_name, annotation_type, data, subs, slot_names=[SLOT_NAME]
        )
    annotation = dt.make_video_annotation(
        per_frame,
        dict.fromkeys(per_frame, True),
        segments_of(per_frame),
        (annotation_type != "point_mask_3d") if interpolated is None else interpolated,
        slot_names=[SLOT_NAME],
    )
    annotation.id = annotation_id or str(uuid.uuid4())
    for a in per_frame.values():
        a.id = annotation.id
    return annotation


def make_lidar_file(
    item_name: str,
    annotations: Sequence[dt.VideoAnnotation],
    frame_count: int,
    coordinate_frame: str = "sensor",
    ego_poses: Optional[Sequence[np.ndarray]] = None,
    timestamps: Optional[Sequence[float]] = None,
    fps: float = 10.0,
    remote_path: str = "/",
) -> dt.AnnotationFile:
    """An ``AnnotationFile`` for the ``pointcloud`` item ``item_name``, ready for Darwin import."""
    frames: List[Dict[str, Any]] = []
    for i in range(frame_count):
        f: Dict[str, Any] = {
            "timestamp": float(timestamps[i]) if timestamps is not None else i / fps
        }
        if coordinate_frame == "world" and ego_poses is not None:
            f["ego_pose"] = np.asarray(ego_poses[i], float).tolist()
        frames.append(f)
    slot = dt.Slot(
        name=SLOT_NAME,
        type="pointcloud",
        source_files=[dt.SourceFile(file_name=item_name)],
        frame_count=frame_count,
        fps=float(fps),
        metadata={"coordinate_frame": coordinate_frame, "frames": frames},
    )
    return dt.AnnotationFile(
        path=Path(item_name).with_suffix(".json"),
        filename=item_name,
        annotation_classes={a.annotation_class for a in annotations},
        annotations=list(annotations),
        remote_path=remote_path,
        slots=[slot],
        frame_count=frame_count,
        version=dt.AnnotationFileVersion(2, 0, ""),
    )


# --- serialization --------------------------------------------------------------------------


def _subs_json(subs: Sequence[dt.SubAnnotation]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for sub in subs:
        key = (
            sub.annotation_type.value
            if isinstance(sub.annotation_type, Enum)
            else str(sub.annotation_type)
        )
        if key == "instance_id":
            out[key] = {"value": sub.data}
        elif key == "text":
            out[key] = {"text": sub.data}
        else:
            out[key] = sub.data
    return out


def _authors(authors: Optional[List[dt.AnnotationAuthor]]) -> List[Dict[str, str]]:
    return [{"full_name": a.name, "email": a.email} for a in authors or []]


def _properties(props: Any) -> List[Dict[str, Any]]:
    return [
        {"frame_index": p.frame_index, "name": p.name, "value": p.value}
        for p in props or []
    ]


def annotation_json(annotation: dt.AnnotationLike) -> Dict[str, Any]:
    """Darwin JSON 2.0 of one annotation (3D video-style annotations, or any single-frame one)."""
    if isinstance(annotation, dt.VideoAnnotation):
        out: Dict[str, Any] = {
            "id": annotation.id,
            "name": annotation.annotation_class.name,
            "slot_names": list(annotation.slot_names),
            "ranges": [list(s) for s in annotation.segments],
            "frames": {
                str(f): {
                    "keyframe": bool(annotation.keyframes.get(f, False)),
                    a.annotation_class.annotation_type: a.data,
                    **_subs_json(a.subs),
                }
                for f, a in sorted(annotation.frames.items())
            },
            "global_sub_types": annotation.global_sub_types or {},
            "properties": _properties(annotation.properties),
        }
        if annotation.interpolated:
            out["interpolated"] = True
        if annotation.interpolate_algorithm:
            out["interpolate_algorithm"] = annotation.interpolate_algorithm
        if annotation.hidden_areas:
            out["hidden_areas"] = annotation.hidden_areas
    else:
        out = {
            "id": annotation.id,
            "name": annotation.annotation_class.name,
            "slot_names": list(annotation.slot_names),
            annotation.annotation_class.annotation_type: annotation.data,
            **_subs_json(annotation.subs),
        }
        if annotation.properties:
            out["properties"] = _properties(annotation.properties)
    if annotation.annotators:
        out["annotators"] = _authors(annotation.annotators)
    if annotation.reviewers:
        out["reviewers"] = _authors(annotation.reviewers)
    return out


def _slot_json(slot: dt.Slot) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "type": slot.type,
        "slot_name": slot.name,
        "source_files": [
            {"file_name": s.file_name, **({"url": s.url} if s.url else {})}
            for s in slot.source_files
        ],
    }
    optional = {
        "fps": slot.fps,
        "thumbnail_url": slot.thumbnail_url,
        "width": slot.width,
        "height": slot.height,
        "frame_count": slot.frame_count,
        "frame_urls": slot.frame_urls,
        "metadata": slot.metadata,
        "segments": slot.segments or None,
    }
    out.update({k: v for k, v in optional.items() if v is not None})
    return out


def to_darwin_json(annotation_file: dt.AnnotationFile) -> Dict[str, Any]:
    """Serializes an ``AnnotationFile`` of a ``pointcloud`` item as Darwin JSON 2.0."""
    source_info = {
        k: v
        for k, v in {
            "item_id": annotation_file.item_id,
            "dataset": (
                {"name": annotation_file.dataset_name}
                if annotation_file.dataset_name
                else None
            ),
            "workview_url": annotation_file.workview_url,
        }.items()
        if v is not None
    }
    item: Dict[str, Any] = {
        "name": annotation_file.filename,
        "path": annotation_file.remote_path or "/",
    }
    if source_info:
        item["source_info"] = source_info
    item["slots"] = [_slot_json(s) for s in annotation_file.slots]
    return {
        "version": "2.0",
        "schema_ref": SCHEMA_REF,
        "item": item,
        "annotations": [annotation_json(a) for a in annotation_file.annotations],
        "properties": annotation_file.item_properties or [],
    }


def write_darwin_json(
    annotation_file: dt.AnnotationFile, output_dir: dt.PathLike
) -> Path:
    """Writes ``<item name without extension>.json`` (the Darwin export file name) to ``output_dir``."""
    path = Path(output_dir) / Path(annotation_file.filename).with_suffix(".json").name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_darwin_json(annotation_file)))
    return path


# --- reading per-frame geometry -------------------------------------------------------------


class FrameObject(NamedTuple):
    annotation: dt.AnnotationLike
    annotation_type: str
    data: Dict[str, Any]
    instance_id: Optional[int]
    attributes: List[str]


def pointcloud_slot(annotation_file: dt.AnnotationFile) -> Optional[dt.Slot]:
    return next((s for s in annotation_file.slots if s.type == "pointcloud"), None)


def instance_id_of(annotation: dt.AnnotationLike) -> Optional[int]:
    """Instance id from the annotation's sub-annotations (any frame) or ``global_sub_types``."""
    frames = (
        annotation.frames.values()
        if isinstance(annotation, dt.VideoAnnotation)
        else [annotation]
    )
    for a in frames:
        sub = a.get_sub("instance_id")
        if sub is not None:
            return int(sub.data)
    gst = getattr(annotation, "global_sub_types", None) or {}
    value = (gst.get("instance_id") or {}).get("value")
    return None if value is None else int(value)


def frame_objects(
    annotation_file: dt.AnnotationFile, types: Sequence[str] = dt.LIDAR_ANNOTATION_TYPES
) -> Dict[int, List[FrameObject]]:
    """
    3D geometry per frame index. Uses the frames present in the file (Darwin exports contain every
    frame of each range, interpolated ones included); single-frame annotations count as frame 0.
    """
    out: Dict[int, List[FrameObject]] = {}
    for annotation in annotation_file.annotations:
        if annotation.annotation_class.annotation_type not in types:
            continue
        instance_id = instance_id_of(annotation)
        frames = (
            annotation.frames.items()
            if isinstance(annotation, dt.VideoAnnotation)
            else [(0, annotation)]
        )
        for f, a in frames:
            attrs = a.get_sub("attributes")
            out.setdefault(int(f), []).append(
                FrameObject(
                    annotation,
                    a.annotation_class.annotation_type,
                    a.data,
                    instance_id,
                    list(attrs.data) if attrs else [],
                )
            )
    return dict(sorted(out.items()))
