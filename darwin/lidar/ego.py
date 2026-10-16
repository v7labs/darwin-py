"""
Ego-frame view of a Darwin LiDAR export: every frame's 3D geometry moved into the ego frame of
that frame's sweep with the slot metadata ``ego_pose`` (what detectors train on).
"""

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

import darwin.datatypes as dt
from darwin.lidar import geometry as g
from darwin.lidar.darwin_json import frame_objects, item_stem, pointcloud_slot


def ego_frame_view(
    annotation_file: dt.AnnotationFile, yaw_only: bool = False
) -> Dict[str, Any]:
    """
    ``{item, coordinate_frame: "ego", frames: [{index, timestamp, ego_pose, annotations}]}`` with
    one entry per frame of the slot. World-frame items need ``ego_pose`` in the slot metadata;
    sensor-frame items are already per sweep and pass through (``ego_pose`` is ``None``).
    ``yaw_only`` drops cuboid roll/pitch after the conversion. Point masks are unchanged.
    """
    slot = pointcloud_slot(annotation_file)
    meta = (slot.metadata if slot else None) or {}
    meta_frames = meta.get("frames") or []
    world = meta.get("coordinate_frame") == "world"
    objects = frame_objects(annotation_file)
    count = max(
        [(slot.frame_count if slot else None) or 0, len(meta_frames)]
        + [f + 1 for f in objects]
    )
    frames: List[Dict[str, Any]] = []
    for i in range(count):
        pose = g.ego_pose_of(meta, i)
        if world and pose is None and objects.get(i):
            raise ValueError(
                f"{annotation_file.filename}: frame {i} is in the world frame but the slot "
                "metadata has no ego_pose for it; re-export the item from Darwin"
            )
        annotations = []
        for o in objects.get(i, []):
            data = (
                o.data
                if pose is None
                else g.to_ego_frame(o.data, pose, o.annotation_type)
            )
            if yaw_only and o.annotation_type == "cuboid_3d":
                data = g.yaw_only(data)
            annotations.append(
                {
                    "id": o.annotation.id,
                    "name": o.annotation.annotation_class.name,
                    "instance_id": o.instance_id,
                    "attributes": o.attributes,
                    o.annotation_type: data,
                }
            )
        frames.append(
            {
                "index": i,
                "timestamp": (meta_frames[i] if i < len(meta_frames) else {}).get(
                    "timestamp"
                ),
                "ego_pose": None if pose is None else pose.tolist(),
                "annotations": annotations,
            }
        )
    return {
        "item": annotation_file.filename,
        "coordinate_frame": "ego",
        "frames": frames,
    }


def export_ego(
    annotation_files: Iterable[dt.AnnotationFile],
    output_dir: dt.PathLike,
    yaw_only: bool = False,
) -> List[Path]:
    """Writes ``<item stem>.ego.json`` (see :func:`ego_frame_view`) per ``pointcloud`` item."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for af in annotation_files:
        if pointcloud_slot(af) is None:
            continue
        path = out / f"{item_stem(af.filename)}.ego.json"
        path.write_text(json.dumps(ego_frame_view(af, yaw_only)))
        paths.append(path)
    return paths
