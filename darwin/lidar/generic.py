"""
Generic point clouds -> Darwin uploads: one cloud -> ``.pcd``, a directory / list of clouds ->
``.lidar.zip`` (sensor frame, or world frame when per-frame poses are given).
"""

import json
from pathlib import Path
from typing import List, Optional, Sequence, Union

import numpy as np
from natsort import natsorted

from darwin.lidar import geometry as g
from darwin.lidar.pointcloud import PathLike, read_points, write_pcd
from darwin.lidar.scene import Frame, package_path, write_scene

CLOUD_SUFFIXES = (".pcd", ".bin", ".ply", ".npy", ".las", ".laz", ".feather")


def cloud_files(source: Union[PathLike, Sequence[PathLike]]) -> List[Path]:
    """The point cloud files of a directory (natural sort), a single file, or a list of files."""
    if isinstance(source, (str, Path)):
        source = Path(source)
        if not source.is_dir():
            return [source]
        return natsorted(
            (p for p in source.iterdir() if p.name.lower().endswith(CLOUD_SUFFIXES)),
            key=lambda p: p.name,
        )
    return [Path(p) for p in source]


def load_poses(source: Union[PathLike, np.ndarray, Sequence]) -> np.ndarray:
    """
    ``(N, 4, 4)`` poses from an array, a ``.npy`` file, a ``.json`` list of 4x4 matrices, or a text
    file with one pose per line as 12 (3x4, KITTI odometry) or 16 (4x4) row-major numbers.
    """
    if isinstance(source, (str, Path)):
        path = Path(source)
        if path.suffix == ".npy":
            source = np.load(path)
        elif path.suffix == ".json":
            source = json.loads(path.read_text())
        else:
            rows = [
                [float(v) for v in line.split()]
                for line in path.read_text().splitlines()
                if line.strip()
            ]
            source = np.array(rows)
    a = np.asarray(source, float)
    if a.ndim == 2 and a.shape[1] in (12, 16):
        a = a.reshape(len(a), -1, 4)
    if a.shape[1:] == (3, 4):
        a = np.concatenate([a, np.tile([[[0, 0, 0, 1.0]]], (len(a), 1, 1))], 1)
    if a.shape[1:] != (4, 4):
        raise ValueError(f"Poses must be 3x4 or 4x4 matrices, got shape {a.shape}")
    return a


def world_to_scene(world_from_ego: np.ndarray) -> np.ndarray:
    """``scene_from_world``: the world translated so the first ego position is the origin."""
    return g.translation(-np.asarray(world_from_ego, float)[0, :3, 3])


def convert_cloud(source: PathLike, output: PathLike) -> Path:
    """Any supported cloud -> float32 binary ``.pcd`` (a single-frame Darwin item, sensor frame)."""
    output = Path(output)
    if output.is_dir() or not output.suffix:
        output.mkdir(parents=True, exist_ok=True)
        output = output / (Path(source).name.split(".")[0] + ".pcd")
    cloud = read_points(source)
    return write_pcd(output, cloud.xyz, cloud.intensity)


def build_pointcloud(
    source: Union[PathLike, Sequence[PathLike]],
    output: PathLike,
    poses: Optional[Union[PathLike, np.ndarray]] = None,
    timestamps: Optional[Sequence[float]] = None,
    name: Optional[str] = None,
    fps: float = 10,
) -> Path:
    """
    A sequence of clouds (a directory, or a list of files, one per frame) -> ``.lidar.zip``.

    Without ``poses`` every frame stays in its own sensor frame (``coordinate_frame="sensor"``).
    With ``poses`` (``world_from_sensor`` per frame, see :func:`load_poses`) the points are moved
    to the scene frame (world translated to the first pose) and ``ego_pose`` is stored per frame.
    """
    files = cloud_files(source)
    if not files:
        raise ValueError(f"No point cloud files in {source}")
    if name is None:
        first = Path(source) if isinstance(source, (str, Path)) else files[0]
        name = first.name.split(".")[0]
    ego = None
    if poses is not None:
        world = load_poses(poses)
        if len(world) < len(files):
            raise ValueError(f"{len(files)} clouds but only {len(world)} poses")
        ego = world_to_scene(world) @ world[: len(files)]

    def frames():
        for i, f in enumerate(files):
            cloud = read_points(f)
            xyz = cloud.xyz if ego is None else g.transform_points(ego[i], cloud.xyz)
            ts = timestamps[i] if timestamps is not None else i / fps
            yield Frame(xyz, cloud.intensity, ts, None if ego is None else ego[i])

    return write_scene(
        package_path(output, name),
        frames(),
        name=name,
        fps=fps,
        coordinate_frame="sensor" if ego is None else "world",
    )
