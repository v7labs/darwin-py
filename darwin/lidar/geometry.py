"""
Rigid transforms for 3D annotations.

Conventions (same as the Darwin LiDAR editor and exports):

- poses are 4x4 row-major matrices ``target_from_source``;
- ``cuboid_3d`` ``rotation`` x/y/z are roll/pitch/yaw in radians, ``R = Rz(yaw) @ Ry(pitch) @ Rx(roll)``;
  ``dimensions`` x/y/z are length (along the heading)/width/height; ``position`` is the box center;
- quaternions are scalar-first ``(w, x, y, z)``.
"""

from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np

Pose = np.ndarray
Geometry = Dict[str, Any]


def quat_to_rot(w: Any, x: Any, y: Any, z: Any) -> np.ndarray:
    """Rotation matrices ``(..., 3, 3)`` from scalar-first quaternions (normalized first)."""
    w, x, y, z = (np.asarray(q, float) for q in (w, x, y, z))
    n = np.sqrt(w * w + x * x + y * y + z * z)
    w, x, y, z = w / n, x / n, y / n, z / n
    return np.stack(
        [
            np.stack(
                [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], -1
            ),
            np.stack(
                [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], -1
            ),
            np.stack(
                [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1
            ),
        ],
        -2,
    )


def rot_to_quat(r: np.ndarray) -> Tuple[float, float, float, float]:
    """Scalar-first unit quaternion ``(w, x, y, z)`` of a 3x3 rotation, with ``w >= 0``."""
    r = np.asarray(r, float)[:3, :3]
    t = np.trace(r)
    if t > 0:
        s = 2 * np.sqrt(t + 1)
        q = [
            s / 4,
            (r[2, 1] - r[1, 2]) / s,
            (r[0, 2] - r[2, 0]) / s,
            (r[1, 0] - r[0, 1]) / s,
        ]
    else:
        i = int(np.argmax(np.diag(r)))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = 2 * np.sqrt(1 + r[i, i] - r[j, j] - r[k, k])
        q = [0.0, 0.0, 0.0, 0.0]
        q[0] = (r[k, j] - r[j, k]) / s
        q[1 + i] = s / 4
        q[1 + j] = (r[j, i] + r[i, j]) / s
        q[1 + k] = (r[k, i] + r[i, k]) / s
    q = np.array(q) / np.linalg.norm(q)
    if q[0] < 0:
        q = -q
    return tuple(float(v) for v in q)  # type: ignore[return-value]


def euler_to_rot(roll: float, pitch: float, yaw: float) -> np.ndarray:
    """``Rz(yaw) @ Ry(pitch) @ Rx(roll)``."""
    cr, sr, cp, sp, cy, sy = (
        np.cos(roll),
        np.sin(roll),
        np.cos(pitch),
        np.sin(pitch),
        np.cos(yaw),
        np.sin(yaw),
    )
    return np.array(
        [
            [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr],
        ]
    )


def rot_to_euler(r: np.ndarray) -> Tuple[float, float, float]:
    """Inverse of :func:`euler_to_rot`: ``(roll, pitch, yaw)``."""
    r = np.asarray(r, float)
    pitch = float(np.arcsin(np.clip(-r[2, 0], -1.0, 1.0)))
    if abs(r[2, 0]) < 1 - 1e-9:
        return (
            float(np.arctan2(r[2, 1], r[2, 2])),
            pitch,
            float(np.arctan2(r[1, 0], r[0, 0])),
        )
    # gimbal lock: fold roll into yaw
    return 0.0, pitch, float(np.arctan2(-r[0, 1], r[1, 1]))


def wrap_angle(a: float) -> float:
    """Angle in ``[-pi, pi)``."""
    return float((a + np.pi) % (2 * np.pi) - np.pi)


def yaw_of(m: np.ndarray) -> float:
    """Heading (rotation about +z) of a rotation or pose matrix."""
    m = np.asarray(m, float)
    return float(np.arctan2(m[1, 0], m[0, 0]))


def make_pose(r: Optional[np.ndarray] = None, t: Sequence[float] = (0, 0, 0)) -> Pose:
    """4x4 pose from a 3x3 rotation and a translation."""
    m = np.eye(4)
    if r is not None:
        m[:3, :3] = r
    m[:3, 3] = t
    return m


def translation(t: Sequence[float]) -> Pose:
    return make_pose(None, t)


def invert(pose: Pose) -> Pose:
    """Inverse of a rigid transform."""
    pose = np.asarray(pose, float)
    return make_pose(pose[:3, :3].T, -pose[:3, :3].T @ pose[:3, 3])


def _vec(p: Dict[str, float]) -> np.ndarray:
    return np.array([p["x"], p["y"], p["z"]], float)


def _dict(v: Sequence[float]) -> Dict[str, float]:
    return {"x": float(v[0]), "y": float(v[1]), "z": float(v[2])}


def cuboid_to_pose(cuboid: Geometry) -> Pose:
    """``frame_from_box`` of a ``cuboid_3d``."""
    r = cuboid.get("rotation") or {"x": 0, "y": 0, "z": 0}
    return make_pose(euler_to_rot(r["x"], r["y"], r["z"]), _vec(cuboid["position"]))


def pose_to_cuboid(pose: Pose, dimensions: Any) -> Geometry:
    """``cuboid_3d`` data from ``frame_from_box`` and ``dimensions`` (dict or length/width/height)."""
    roll, pitch, yaw = rot_to_euler(np.asarray(pose)[:3, :3])
    dims = dimensions if isinstance(dimensions, dict) else _dict(dimensions)
    return {
        "position": _dict(np.asarray(pose)[:3, 3]),
        "dimensions": {k: float(dims[k]) for k in "xyz"},
        "rotation": {"x": roll, "y": pitch, "z": yaw},
    }


def transform_points(pose: Pose, xyz: np.ndarray) -> np.ndarray:
    """Applies a 4x4 pose to ``(N, 3)`` points."""
    pose = np.asarray(pose, float)
    return np.asarray(xyz, float) @ pose[:3, :3].T + pose[:3, 3]


def transform_geometry(annotation_type: str, data: Geometry, pose: Pose) -> Geometry:
    """
    Moves the geometry of one frame of a 3D annotation with ``pose`` (``target_from_source``).
    ``point_mask_3d`` (point indices) is returned unchanged.
    """
    if annotation_type == "cuboid_3d":
        return pose_to_cuboid(
            np.asarray(pose) @ cuboid_to_pose(data), data["dimensions"]
        )
    if annotation_type in ("polyline_3d", "polygon_3d"):
        pts = transform_points(
            pose, np.array([_vec(p) for p in data["path"]]).reshape(-1, 3)
        )
        return {**data, "path": [_dict(p) for p in pts]}
    if annotation_type == "keypoint_3d":
        return _dict(transform_points(pose, _vec(data)[None])[0])
    if annotation_type == "point_mask_3d":
        return data
    raise ValueError(f"Not a 3D annotation type: '{annotation_type}'")


def to_ego_frame(
    data: Geometry, ego_pose: Pose, annotation_type: str = "cuboid_3d"
) -> Geometry:
    """
    Scene-frame geometry of one frame -> the ego frame of that frame's sweep.
    ``ego_pose`` is the slot metadata ``frames[t].ego_pose`` (4x4 ``scene_from_ego``).
    Cuboids keep their full rotation; use :func:`yaw_only` for heading-only boxes.
    """
    return transform_geometry(annotation_type, data, invert(ego_pose))


def to_scene_frame(
    data: Geometry, ego_pose: Pose, annotation_type: str = "cuboid_3d"
) -> Geometry:
    """Inverse of :func:`to_ego_frame`."""
    return transform_geometry(annotation_type, data, np.asarray(ego_pose, float))


def yaw_only(cuboid: Geometry) -> Geometry:
    """Drops roll and pitch, keeping the heading of the box's length axis."""
    yaw = yaw_of(cuboid_to_pose(cuboid))
    return {**cuboid, "rotation": {"x": 0.0, "y": 0.0, "z": yaw}}


def box_corners(cuboid: Geometry) -> np.ndarray:
    """``(8, 3)`` corners: 0-3 bottom, 4-7 top, both front-left, front-right, rear-right, rear-left."""
    d = cuboid["dimensions"]
    x = np.array([1, 1, -1, -1] * 2) * d["x"] / 2
    y = np.array([1, -1, -1, 1] * 2) * d["y"] / 2
    z = np.array([-1] * 4 + [1] * 4) * d["z"] / 2
    return transform_points(cuboid_to_pose(cuboid), np.stack([x, y, z], 1))


def ego_pose_of(slot_metadata: Optional[Dict[str, Any]], frame: int) -> Optional[Pose]:
    """
    ``scene_from_ego`` of a frame from ``pointcloud`` slot metadata, or ``None`` when the slot is
    in the sensor frame (geometry is already per-sweep) or the pose is missing.
    """
    meta = slot_metadata or {}
    frames = meta.get("frames") or []
    if meta.get("coordinate_frame") != "world" or frame >= len(frames):
        return None
    pose = frames[frame].get("ego_pose")
    return None if pose is None else np.asarray(pose, float)
