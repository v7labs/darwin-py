"""
Argoverse 2 (Sensor dataset) logs: scene packages, ``annotations.feather`` import and export.

Frames: one per lidar sweep (``sensors/lidar/<timestamp_ns>.feather``, ego frame, every point
in file order). Scene frame: the city frame translated so the ego at the first sweep is the
origin. Ego frame: AV2's ``egovehicle`` frame (rear axle center, no ground offset), so
ego-frame exports match ``annotations.feather`` directly. Needs ``pyarrow``.
"""

import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence

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
from darwin.lidar.pointcloud import PathLike, missing_dependency
from darwin.lidar.scene import CameraImage, Frame, package_path, write_scene

RING_CAMERAS = (
    "ring_front_center",
    "ring_front_left",
    "ring_front_right",
    "ring_side_left",
    "ring_side_right",
    "ring_rear_left",
    "ring_rear_right",
)
COLUMNS = (
    "timestamp_ns",
    "track_uuid",
    "category",
    "length_m",
    "width_m",
    "height_m",
    "qw",
    "qx",
    "qy",
    "qz",
    "tx_m",
    "ty_m",
    "tz_m",
    "num_interior_pts",
)


def _pyarrow() -> Any:
    try:
        import pyarrow
        import pyarrow.feather  # noqa: F401
    except ImportError:
        raise missing_dependency("pyarrow", "lidar_av2") from None
    return pyarrow


def read_feather_table(path: PathLike) -> Dict[str, np.ndarray]:
    table = _pyarrow().feather.read_table(str(path))
    return {k: np.asarray(v) for k, v in table.to_pydict().items()}


def se3(table: Dict[str, np.ndarray]) -> np.ndarray:
    """``(N, 4, 4)`` poses from AV2 ``qw qx qy qz tx_m ty_m tz_m`` columns."""
    m = np.tile(np.eye(4), (len(table["qw"]), 1, 1))
    m[:, :3, :3] = g.quat_to_rot(table["qw"], table["qx"], table["qy"], table["qz"])
    m[:, :3, 3] = np.stack([table["tx_m"], table["ty_m"], table["tz_m"]], 1)
    return m


class Log:
    """Sweep timestamps, poses and the scene frame of one AV2 log."""

    def __init__(self, log_dir: PathLike):
        self.dir = Path(log_dir)
        self.id = self.dir.name
        self.sweeps = sorted(
            (self.dir / "sensors" / "lidar").glob("*.feather"),
            key=lambda p: int(p.stem),
        )
        if not self.sweeps:
            raise FileNotFoundError(
                f"No lidar sweeps in {self.dir / 'sensors' / 'lidar'}"
            )
        self.ts = np.array([int(p.stem) for p in self.sweeps], np.int64)
        poses = read_feather_table(self.dir / "city_SE3_egovehicle.feather")
        order = np.argsort(poses["timestamp_ns"])
        self._pose_ts = poses["timestamp_ns"].astype(np.int64)[order]
        self._poses = se3(poses)[order]
        city_from_ego = self.city_from_ego(self.ts)
        self.scene_from_city = g.translation(-city_from_ego[0, :3, 3])
        #: ``scene_from_ego`` per sweep
        self.ego_poses = self.scene_from_city @ city_from_ego

    def city_from_ego(self, ts_ns: Any) -> np.ndarray:
        # ponytail: nearest pose, no interpolation (AV2 poses are denser than sweeps and images)
        ts = np.atleast_1d(np.asarray(ts_ns, np.int64))
        n = len(self._pose_ts)
        i = np.searchsorted(self._pose_ts, ts).clip(0, n - 1)
        prev = (i - 1).clip(0, n - 1)
        near_prev = np.abs(self._pose_ts[prev] - ts) <= np.abs(self._pose_ts[i] - ts)
        return self._poses[np.where(near_prev, prev, i)]

    @property
    def item_name(self) -> str:
        return f"{self.id}.lidar.zip"

    @property
    def timestamps(self) -> np.ndarray:
        return (self.ts - self.ts[0]) / 1e9


def build_av2(
    log_dir: PathLike,
    output: PathLike,
    cameras: Optional[Sequence[str]] = None,
    image_scale: float = 0.5,
) -> Path:
    """One AV2 log -> ``<log_id>.lidar.zip`` (world frame, ring cameras as per-frame JPEGs)."""
    log = Log(log_dir)
    calib = read_feather_table(
        log.dir / "calibration" / "egovehicle_SE3_sensor.feather"
    )
    ego_from_sensor = dict(zip(calib["sensor_name"], se3(calib)))
    intr = read_feather_table(log.dir / "calibration" / "intrinsics.feather")
    city_from_scene = g.invert(log.scene_from_city)
    cams = []
    for cam in cameras or RING_CAMERAS:
        files = sorted(
            (log.dir / "sensors" / "cameras" / cam).glob("*.jpg"),
            key=lambda p: int(p.stem),
        )
        if not files:
            continue
        j = list(intr["sensor_name"]).index(cam)
        k = np.array(
            [
                [intr["fx_px"][j], 0, intr["cx_px"][j]],
                [0, intr["fy_px"][j], intr["cy_px"][j]],
                [0, 0, 1],
            ]
        )
        cam_from_ego = g.invert(ego_from_sensor[cam])[:3]
        its = np.array([int(p.stem) for p in files], np.int64)
        nearest = np.abs(its[None, :] - log.ts[:, None]).argmin(1)
        cams.append((cam, files, its, nearest, k @ cam_from_ego))

    def frames() -> Iterator[Frame]:
        for i, sweep in enumerate(log.sweeps):
            d = read_feather_table(sweep)
            xyz = np.stack([d["x"], d["y"], d["z"]], 1).astype(float)
            images = {}
            for cam, files, its, nearest, p in cams:
                j = nearest[i]
                ego_from_city = g.invert(log.city_from_ego(its[j])[0])
                images[cam] = CameraImage(files[j], p @ ego_from_city @ city_from_scene)
            yield Frame(
                g.transform_points(log.ego_poses[i], xyz),
                d.get("intensity"),
                log.ts[i] / 1e9,
                log.ego_poses[i],
                images,
            )

    return write_scene(
        package_path(output, log.id),
        frames(),
        name=f"Argoverse 2 {log.id}",
        fps=10,
        coordinate_frame="world",
        image_scale=image_scale,
    )


def parse_av2(path: PathLike) -> List[dt.AnnotationFile]:
    """
    ``annotations.feather`` (or its log directory) -> one ``AnnotationFile`` for
    ``<log_id>.lidar.zip``: a ``cuboid_3d`` track per ``track_uuid`` in the scene frame
    (full rotation), ``instance_id`` = 1-based order of first appearance, class = ``category``.
    """
    path = Path(path)
    log = Log(path.parent if path.is_file() else path)
    ann = read_feather_table(log.dir / "annotations.feather")
    frame_of = {int(t): i for i, t in enumerate(log.ts)}
    tracks: Dict[str, Dict[str, Any]] = {}
    boxes = se3(ann)
    for r in np.lexsort((np.arange(len(boxes)), ann["timestamp_ns"])):
        f = frame_of.get(int(ann["timestamp_ns"][r]))
        if f is None:
            raise ValueError(
                f"Annotation at {ann['timestamp_ns'][r]} matches no lidar sweep"
            )
        dims = (ann["length_m"][r], ann["width_m"][r], ann["height_m"][r])
        track = tracks.setdefault(
            str(ann["track_uuid"][r]),
            {"category": str(ann["category"][r]), "frames": {}},
        )
        track["frames"][f] = g.pose_to_cuboid(log.ego_poses[f] @ boxes[r], dims)
    annotations = [
        make_track(t["category"], "cuboid_3d", t["frames"], instance_id=n + 1)
        for n, t in enumerate(tracks.values())
    ]
    return [
        make_lidar_file(
            log.item_name,
            annotations,
            len(log.ts),
            "world",
            ego_poses=log.ego_poses,
            timestamps=log.timestamps,
            fps=10,
        )
    ]


def export_av2(
    annotation_files: Iterable[dt.AnnotationFile],
    output_dir: PathLike,
    log_dir: Optional[PathLike] = None,
) -> None:
    """
    Writes ``<output_dir>/<item stem>/annotations.feather`` with every ``cuboid_3d`` in the ego frame
    of its sweep. ``timestamp_ns`` is the slot's frame timestamp (nanoseconds since the first sweep),
    or the sweep's AV2 timestamp when ``log_dir`` is given. ``track_uuid`` is a UUID5 of the Darwin
    annotation id; ``num_interior_pts`` is ``-1``. Sensor-frame items are written as they are.
    """
    pa = _pyarrow()
    sweep_ts = Log(log_dir).ts if log_dir is not None else None
    for af in annotation_files:
        slot = pointcloud_slot(af)
        if slot is None:
            continue
        meta = slot.metadata or {}
        meta_frames = meta.get("frames") or []
        rows: Dict[str, List[Any]] = {c: [] for c in COLUMNS}
        for f, objects in frame_objects(af, ["cuboid_3d"]).items():
            if meta.get("coordinate_frame") == "world":
                ego = g.ego_pose_of(meta, f)
                if ego is None:
                    print(
                        f"[WARNING] {af.filename}: no ego pose for frame {f}, skipped"
                    )
                    continue
            else:
                ego = np.eye(4)
            if sweep_ts is not None:
                ts = int(sweep_ts[f])
            else:
                ts = (
                    int(round(float(meta_frames[f]["timestamp"]) * 1e9))
                    if f < len(meta_frames)
                    else f
                )
            for o in objects:
                box = g.to_ego_frame(o.data, ego)
                qw, qx, qy, qz = g.rot_to_quat(g.cuboid_to_pose(box))
                d, p = box["dimensions"], box["position"]
                key = o.annotation.id or f"{af.filename}/{id(o.annotation)}"
                values = (
                    ts,
                    str(uuid.uuid5(uuid.NAMESPACE_OID, key)),
                    o.annotation.annotation_class.name,
                    d["x"],
                    d["y"],
                    d["z"],
                    qw,
                    qx,
                    qy,
                    qz,
                    p["x"],
                    p["y"],
                    p["z"],
                    -1,
                )
                for c, v in zip(COLUMNS, values):
                    rows[c].append(v)
        out = Path(output_dir) / item_stem(af.filename)
        out.mkdir(parents=True, exist_ok=True)
        types = {c: pa.float64() for c in COLUMNS}
        types.update(
            timestamp_ns=pa.int64(),
            num_interior_pts=pa.int64(),
            track_uuid=pa.string(),
            category=pa.string(),
        )
        table = pa.table({c: pa.array(rows[c], types[c]) for c in COLUMNS})
        pa.feather.write_feather(table, str(out / "annotations.feather"))
