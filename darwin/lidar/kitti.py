"""
KITTI (object, tracking, raw) <-> Darwin LiDAR.

- Builders: velodyne ``.bin`` + ``image_02`` / ``image_2`` + calib -> ``.lidar.zip``. Sensor
  (velodyne) frame by default; ``world=True`` uses the OXTS poses (KITTI devkit Mercator
  projection), ego = velodyne, scene = world translated to the first velodyne position.
- Importers: ``label_2`` (object), ``label_02`` (tracking) and raw ``tracklet_labels.xml`` ->
  ``cuboid_3d`` tracks in the velodyne / scene frame.
- Exporter: OpenPCDet-style lidar-frame labels, or real KITTI ``label_2`` / ``label_02`` lines
  in the rectified camera frame when calib is given.
"""

import calendar
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import (
    Dict,
    Iterable,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Union,
)

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
from darwin.lidar.generic import world_to_scene
from darwin.lidar.pointcloud import PathLike, read_bin
from darwin.lidar.scene import CameraImage, Frame, package_path, write_scene

CAMERA = "front"
#: KITTI images are rectified: undistorted pinhole
PINHOLE = {"model": "pinhole"}


class Calib(NamedTuple):
    #: 3x4 projection of the rectified left color camera.
    P2: np.ndarray
    #: 4x4 rectifying rotation.
    R0: np.ndarray
    #: 4x4 ``cam0_from_velo``.
    velo_to_cam: np.ndarray
    #: 4x4 ``velo_from_imu``, when known.
    imu_to_velo: Optional[np.ndarray] = None
    #: ``(width, height)`` of the rectified images, when known.
    image_size: Optional[Tuple[int, int]] = None

    @property
    def velo_to_rect(self) -> np.ndarray:
        return self.R0 @ self.velo_to_cam

    @property
    def velo_to_image(self) -> np.ndarray:
        return self.P2 @ self.velo_to_rect

    @property
    def camera(self) -> Tuple[np.ndarray, np.ndarray]:
        """``(K, camera_from_velo)`` of the left color camera (``K @ camera_from_velo[:3] = velo_to_image``)."""
        k, cam_from_rect = g.split_projection(self.P2)
        return k, cam_from_rect @ self.velo_to_rect


def _read_kv(path: PathLike) -> Dict[str, np.ndarray]:
    """``key: numbers`` and ``key numbers`` lines (KITTI object / tracking / raw calib files)."""
    out = {}
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        key, _, rest = line.partition(":") if ":" in line else line.partition(" ")
        try:
            out[key.strip()] = np.array([float(v) for v in rest.split()])
        except ValueError:
            pass
    return out


def _h(m: np.ndarray) -> np.ndarray:
    """3x3 or 3x4 -> 4x4."""
    out = np.eye(4)
    out[: m.shape[0], : m.shape[1]] = m
    return out


def _rt(kv: Dict[str, np.ndarray]) -> np.ndarray:
    return g.make_pose(kv["R"].reshape(3, 3), kv["T"])


def load_calib(path: Union[PathLike, Calib]) -> Calib:
    """A KITTI object/tracking calib file, or a KITTI raw date directory with ``calib_*.txt``."""
    if isinstance(path, Calib):
        return path
    path = Path(path)
    if path.is_dir():
        c2c = _read_kv(path / "calib_cam_to_cam.txt")
        imu = path / "calib_imu_to_velo.txt"
        size = c2c.get("S_rect_02")
        return Calib(
            c2c["P_rect_02"].reshape(3, 4),
            _h(c2c["R_rect_00"].reshape(3, 3)),
            _rt(_read_kv(path / "calib_velo_to_cam.txt")),
            _rt(_read_kv(imu)) if imu.exists() else None,
            None if size is None else (int(size[0]), int(size[1])),
        )
    kv = _read_kv(path)
    r0 = kv.get("R0_rect", kv.get("R_rect"))
    tr = kv.get("Tr_velo_to_cam", kv.get("Tr_velo_cam"))
    imu = kv.get("Tr_imu_to_velo", kv.get("Tr_imu_velo"))
    return Calib(
        kv["P2"].reshape(3, 4),
        _h(r0.reshape(3, 3)) if r0 is not None else np.eye(4),
        _h(tr.reshape(3, 4)),
        None if imu is None else _h(imu.reshape(3, 4)),
    )


# --- poses ----------------------------------------------------------------------------------


def oxts_poses(oxts: np.ndarray) -> np.ndarray:
    """``world_from_imu`` per OXTS row (lat, lon, alt, roll, pitch, yaw, ...), KITTI devkit Mercator."""
    oxts = np.atleast_2d(np.asarray(oxts, float))
    er, scale = 6378137.0, np.cos(np.deg2rad(oxts[0, 0]))
    poses = []
    for lat, lon, alt, roll, pitch, yaw in oxts[:, :6]:
        t = (
            scale * np.deg2rad(lon) * er,
            scale * er * np.log(np.tan(np.deg2rad(90 + lat) / 2)),
            alt,
        )
        poses.append(g.make_pose(g.euler_to_rot(roll, pitch, yaw), t))
    return np.array(poses)


def read_oxts(source: PathLike) -> np.ndarray:
    """OXTS rows from a tracking ``oxts/<seq>.txt`` or a raw ``oxts/data`` directory."""
    source = Path(source)
    files = sorted(source.glob("*.txt")) if source.is_dir() else [source]
    rows = [
        line.split()
        for f in files
        for line in f.read_text().splitlines()
        if line.strip()
    ]
    return np.array(rows, float)


def world_poses(oxts: np.ndarray, calib: Calib) -> np.ndarray:
    """``world_from_velo`` per frame from the OXTS poses (KITTI devkit Mercator world)."""
    if calib.imu_to_velo is None:
        raise ValueError("World-frame KITTI needs the IMU -> velodyne calibration")
    return oxts_poses(oxts) @ np.linalg.inv(calib.imu_to_velo)


def ego_poses(oxts: np.ndarray, calib: Calib) -> np.ndarray:
    """``scene_from_velo`` per frame: world from the OXTS poses, translated to the first frame."""
    world_from_velo = world_poses(oxts, calib)
    return world_to_scene(world_from_velo) @ world_from_velo


def _raw_timestamps(path: Path) -> Optional[List[float]]:
    if not path.exists():
        return None
    out = []
    for line in path.read_text().split("\n"):
        if line.strip():
            date, _, frac = line.strip().partition(".")
            stamp = calendar.timegm(time.strptime(date, "%Y-%m-%d %H:%M:%S"))
            out.append(stamp + float("0." + (frac or "0")))
    return out


# --- builders -------------------------------------------------------------------------------


def _build(
    path: Path,
    name: str,
    velo_files: Sequence[Path],
    image_dir: Optional[Path],
    calib: Calib,
    timestamps: Optional[Sequence[float]],
    image_scale: float,
    fps: float = 10,
    world: Optional[np.ndarray] = None,
) -> Path:
    """``world``: ``world_from_velo`` per frame for a world-frame scene (sensor frame without)."""
    ego = None if world is None else world_to_scene(world) @ world
    if ego is not None and len(ego) < len(velo_files):
        raise ValueError(f"{len(velo_files)} velodyne frames but {len(ego)} OXTS poses")
    k, cam_from_velo = calib.camera

    def frames():
        for i, f in enumerate(velo_files):
            cloud = read_bin(f)
            cfw = cam_from_velo
            xyz = cloud.xyz
            if ego is not None:
                xyz, cfw = g.transform_points(ego[i], xyz), cfw @ g.invert(ego[i])
            image = None if image_dir is None else image_dir / f"{f.stem}.png"
            images = (
                {CAMERA: CameraImage(image, None, k, cfw, PINHOLE)}
                if image and image.exists()
                else {}
            )
            ts = timestamps[i] if timestamps else i / fps
            yield Frame(
                xyz, cloud.intensity, ts, None if ego is None else ego[i], images
            )

    return write_scene(
        path,
        frames(),
        name=name,
        fps=fps,
        coordinate_frame="sensor" if ego is None else "world",
        image_scale=image_scale,
        origin=None if world is None else world[0, :3, 3],
    )


def build_kitti_raw(
    drive_dir: PathLike,
    output: PathLike,
    calib_dir: Optional[PathLike] = None,
    world: bool = False,
    image_scale: float = 0.5,
) -> Path:
    """A KITTI raw ``<date>_drive_<n>_sync`` directory -> ``<drive>.lidar.zip``."""
    drive = Path(drive_dir)
    calib = load_calib(calib_dir or drive.parent)
    velo = sorted((drive / "velodyne_points" / "data").glob("*.bin"))
    poses = world_poses(read_oxts(drive / "oxts" / "data"), calib) if world else None
    ts = _raw_timestamps(drive / "velodyne_points" / "timestamps.txt")
    return _build(
        package_path(output, drive.name),
        drive.name,
        velo,
        drive / "image_02" / "data",
        calib,
        ts,
        image_scale,
        world=poses,
    )


def _split_dir(root: PathLike, split: str) -> Path:
    root = Path(root)
    return root / split if (root / split).is_dir() else root


def _seq(sequence: Union[int, str]) -> str:
    return f"{int(sequence):04d}" if str(sequence).isdigit() else str(sequence)


def build_kitti_tracking(
    root: PathLike,
    sequence: Union[int, str],
    output: PathLike,
    split: str = "training",
    world: bool = False,
    image_scale: float = 0.5,
) -> Path:
    """KITTI tracking ``<root>/<split>/{velodyne,image_02}/<seq>`` -> ``kitti_tracking_<split>_<seq>.lidar.zip``."""
    base, seq = _split_dir(root, split), _seq(sequence)
    calib = load_calib(base / "calib" / f"{seq}.txt")
    velo = sorted((base / "velodyne" / seq).glob("*.bin"))
    poses = (
        world_poses(read_oxts(base / "oxts" / f"{seq}.txt"), calib) if world else None
    )
    name = f"kitti_tracking_{split}_{seq}"
    return _build(
        package_path(output, name),
        name,
        velo,
        base / "image_02" / seq,
        calib,
        None,
        image_scale,
        world=poses,
    )


def build_kitti_object(
    root: PathLike,
    output: PathLike,
    split: str = "training",
    frame_ids: Optional[Iterable[Union[int, str]]] = None,
    image_scale: float = 0.5,
) -> List[Path]:
    """KITTI object detection -> one single-frame ``kitti_object_<split>_<id>.lidar.zip`` per frame."""
    base = _split_dir(root, split)
    if frame_ids is None:
        ids = [p.stem for p in sorted((base / "velodyne").glob("*.bin"))]
    else:
        ids = [f"{int(i):06d}" if str(i).isdigit() else str(i) for i in frame_ids]
    out = []
    for i in ids:
        name = f"kitti_object_{split}_{i}"
        out.append(
            _build(
                package_path(output, name),
                name,
                [base / "velodyne" / f"{i}.bin"],
                base / "image_2",
                load_calib(base / "calib" / f"{i}.txt"),
                None,
                image_scale,
            )
        )
    return out


# --- label conversion -----------------------------------------------------------------------


def camera_box_to_velo(
    h: float,
    w: float,
    length: float,
    loc: Sequence[float],
    ry: float,
    calib: Calib,
) -> Dict:
    """KITTI camera box (bottom-center ``loc``, ``rotation_y``) -> ``cuboid_3d`` in the velodyne frame."""
    c, s = np.cos(ry), np.sin(ry)
    # box axes in the rectified camera frame: length (heading), width, up (= -y)
    rect_from_box = g.make_pose(
        np.array([[c, s, 0], [0, 0, -1], [-s, c, 0]]),
        (loc[0], loc[1] - h / 2, loc[2]),
    )
    velo_from_box = np.linalg.inv(calib.velo_to_rect) @ rect_from_box
    return g.pose_to_cuboid(velo_from_box, (length, w, h))


def velo_box_to_camera(
    cuboid: Dict, calib: Calib
) -> Tuple[float, float, float, np.ndarray, float]:
    """Inverse of :func:`camera_box_to_velo`: ``(h, w, l, bottom-center loc, rotation_y)``."""
    rect_from_box = calib.velo_to_rect @ g.cuboid_to_pose(cuboid)
    d = cuboid["dimensions"]
    x_axis = rect_from_box[:3, 0]
    ry = float(np.arctan2(-x_axis[2], x_axis[0]))
    loc = rect_from_box[:3, 3] + np.array([0, d["z"] / 2, 0])
    return d["z"], d["y"], d["x"], loc, ry


def _label_rows(path: Path, tracking: bool) -> List[List[str]]:
    rows = [line.split() for line in path.read_text().splitlines() if line.strip()]
    type_col = 2 if tracking else 0
    return [r for r in rows if r[type_col] != "DontCare"]


def _box(row: Sequence[str], calib: Calib) -> Dict:
    h, w, length, x, y, z, ry = (float(v) for v in row[8:15])
    return camera_box_to_velo(h, w, length, (x, y, z), ry, calib)


def parse_kitti_labels(
    label_file: PathLike,
    calib_file: Optional[PathLike] = None,
    item_name: Optional[str] = None,
) -> List[dt.AnnotationFile]:
    """KITTI object ``label_2/<id>.txt`` -> one single-frame file for ``kitti_object_<split>_<id>.lidar.zip``."""
    label_file = Path(label_file)
    split_dir = label_file.parent.parent
    calib = load_calib(calib_file or split_dir / "calib" / f"{label_file.stem}.txt")
    tracks = [
        make_track(r[0], "cuboid_3d", {0: _box(r, calib)})
        for r in _label_rows(label_file, False)
    ]
    name = item_name or f"kitti_object_{split_dir.name}_{label_file.stem}.lidar.zip"
    return [make_lidar_file(name, tracks, 1, "sensor")]


def _frame_count(velo_dir: Path, fallback: int) -> int:
    n = len(list(velo_dir.glob("*.bin"))) if velo_dir.is_dir() else 0
    return max(n, fallback)


def _to_scene(boxes: Dict[int, Dict], ego: Optional[np.ndarray]) -> Dict[int, Dict]:
    if ego is None:
        return boxes
    return {f: g.to_scene_frame(b, ego[f]) for f, b in boxes.items()}


def parse_kitti_tracking(
    label_file: PathLike,
    calib_file: Optional[PathLike] = None,
    oxts_file: Optional[PathLike] = None,
    world: bool = False,
    split: Optional[str] = None,
    item_name: Optional[str] = None,
) -> List[dt.AnnotationFile]:
    """KITTI tracking ``label_02/<seq>.txt`` -> one file for ``kitti_tracking_<split>_<seq>.lidar.zip``."""
    label_file = Path(label_file)
    split_dir, seq = label_file.parent.parent, label_file.stem
    calib = load_calib(calib_file or split_dir / "calib" / f"{seq}.txt")
    rows = _label_rows(label_file, True)
    tracks: Dict[int, Tuple[str, Dict[int, Dict]]] = {}
    for r in rows:
        tracks.setdefault(int(r[1]), (r[2], {}))[1][int(r[0])] = _box(r[2:], calib)
    n = _frame_count(
        split_dir / "velodyne" / seq, max((int(r[0]) for r in rows), default=-1) + 1
    )
    ego = None
    if world:
        ego = ego_poses(
            read_oxts(oxts_file or split_dir / "oxts" / f"{seq}.txt"), calib
        )
        n = max(n, len(ego))
    annotations = [
        make_track(cls, "cuboid_3d", _to_scene(boxes, ego), instance_id=tid + 1)
        for tid, (cls, boxes) in sorted(tracks.items())
    ]
    name = item_name or f"kitti_tracking_{split or split_dir.name}_{seq}.lidar.zip"
    return [make_lidar_file(name, annotations, n, "world" if world else "sensor", ego)]


def parse_kitti_tracklets(
    xml_path: PathLike,
    oxts_dir: Optional[PathLike] = None,
    world: bool = False,
    item_name: Optional[str] = None,
    calib_dir: Optional[PathLike] = None,
) -> List[dt.AnnotationFile]:
    """KITTI raw ``<drive>/tracklet_labels.xml`` (velodyne frame) -> one file for ``<drive>.lidar.zip``."""
    xml_path = Path(xml_path)
    drive = xml_path.parent
    root = ET.parse(xml_path).getroot()
    tracks = []
    for item in root.find("tracklets").findall("item"):
        h, w, length = (float(item.find(k).text) for k in ("h", "w", "l"))
        first = int(item.find("first_frame").text)
        boxes = {}
        for k, p in enumerate(item.find("poses").findall("item")):
            tx, ty, tz, rx, ry, rz = (
                float(p.find(a).text) for a in ("tx", "ty", "tz", "rx", "ry", "rz")
            )
            r = g.euler_to_rot(rx, ry, rz)
            center = np.array([tx, ty, tz]) + r @ [0, 0, h / 2]  # tz is the box bottom
            boxes[first + k] = g.pose_to_cuboid(g.make_pose(r, center), (length, w, h))
        if boxes:
            tracks.append((item.find("objectType").text, boxes))
    n = _frame_count(
        drive / "velodyne_points" / "data",
        max((max(b) for _, b in tracks), default=-1) + 1,
    )
    ego = None
    if world:
        calib = load_calib(calib_dir or drive.parent)
        ego = ego_poses(read_oxts(oxts_dir or drive / "oxts" / "data"), calib)
        n = max(n, len(ego))
    annotations = [
        make_track(cls, "cuboid_3d", _to_scene(boxes, ego), instance_id=k + 1)
        for k, (cls, boxes) in enumerate(tracks)
    ]
    name = item_name or f"{drive.name}.lidar.zip"
    return [make_lidar_file(name, annotations, n, "world" if world else "sensor", ego)]


# --- exporter -------------------------------------------------------------------------------


def _bbox(
    cuboid_velo: Dict, calib: Calib, image_size: Optional[Tuple[int, int]]
) -> List[float]:
    corners = g.box_corners(cuboid_velo)
    uvw = np.c_[corners, np.ones(8)] @ calib.velo_to_image.T
    front = uvw[uvw[:, 2] > 1e-3]
    if not len(front):
        return [0.0] * 4
    uv = front[:, :2] / front[:, 2:3]
    x1, y1 = uv.min(0)
    x2, y2 = uv.max(0)
    if image_size:
        x1, x2 = np.clip([x1, x2], 0, image_size[0] - 1)
        y1, y2 = np.clip([y1, y2], 0, image_size[1] - 1)
    return [float(x1), float(y1), float(x2), float(y2)]


def _fmt(values: Iterable[float]) -> str:
    return " ".join(f"{v:.6f}" for v in values)


def kitti_line(
    cuboid_velo: Dict,
    cls: str,
    calib: Calib,
    image_size: Optional[Tuple[int, int]] = None,
) -> str:
    """One KITTI ``label_2`` line (truncated / occluded 0, alpha and 2D box derived)."""
    h, w, length, loc, ry = velo_box_to_camera(cuboid_velo, calib)
    alpha = g.wrap_angle(ry - np.arctan2(loc[0], loc[2]))
    bbox = _bbox(cuboid_velo, calib, image_size)
    return f"{cls} 0.00 0 {alpha:.6f} {_fmt(bbox)} {_fmt([h, w, length])} {_fmt(loc)} {ry:.6f}"


def openpcdet_line(cuboid: Dict, cls: str) -> str:
    """``x y z dx dy dz heading class`` (box center, lidar frame)."""
    p, d = cuboid["position"], cuboid["dimensions"]
    heading = g.yaw_of(g.cuboid_to_pose(cuboid))
    return f"{_fmt([p['x'], p['y'], p['z'], d['x'], d['y'], d['z'], heading])} {cls}"


def _calib_for(calib, name: str) -> Optional[Calib]:
    if calib is None:
        return None
    if isinstance(calib, Mapping):
        calib = calib.get(name)
        return None if calib is None else load_calib(calib)
    return load_calib(calib)


def _export_camera(meta: Optional[Dict], camera: Optional[str]) -> Optional[str]:
    """``camera``, else the first calibrated pinhole camera of the export (``front`` first)."""
    cams = g.slot_cameras(meta)
    if camera is not None:
        return camera if g.intrinsics_matrix(cams.get(camera)) is not None else None
    for name in sorted(cams, key=lambda n: n != CAMERA):
        model = (cams[name].get("distortion") or PINHOLE)["model"]
        if g.intrinsics_matrix(cams[name]) is not None and model == "pinhole":
            return name
    return None


def _export_calib(meta: Optional[Dict], f: int, camera: str) -> Optional[Calib]:
    """Calib of ``camera``'s image of frame ``f`` from the export: ``P2 = [K | 0]``, velodyne = ego frame."""
    cam = g.slot_cameras(meta)[camera]
    cfw = g.camera_from_world_of(meta, f, camera)
    if cfw is None:
        return None
    ego = g.ego_pose_of(meta, f)
    cam_from_ego = cfw if ego is None else cfw @ ego
    k = g.intrinsics_matrix(cam)
    size = (int(cam["width"]), int(cam["height"])) if "width" in cam else None
    return Calib(np.c_[k, np.zeros(3)], np.eye(4), cam_from_ego, None, size)


def export_kitti(
    annotation_files: Iterable[dt.AnnotationFile],
    output_dir: PathLike,
    calib: Optional[
        Union[PathLike, Calib, Mapping[str, Union[PathLike, Calib]]]
    ] = None,
    tracking: bool = False,
    image_size: Optional[Tuple[int, int]] = None,
    camera: Optional[str] = None,
) -> None:
    """
    ``cuboid_3d`` annotations of pointcloud items -> KITTI-style text labels, in the lidar (ego)
    frame of each sweep (world-frame items are converted with the slot's ego poses).

    - no ``calib``: ``<output>/<item>/<frame:06d>.txt`` with ``x y z dx dy dz heading class``;
    - ``calib`` (a calib file / raw calib dir / ``Calib``, or a mapping item name -> calib):
      KITTI ``label_2`` lines in the rectified camera frame, ``<output>/<item>.txt`` for
      single-frame items, ``<output>/<item>/<frame:06d>.txt`` otherwise;
    - ``tracking=True``: ``<output>/<item>.txt`` in the ``label_02`` format,
      ``track_id = instance_id - 1`` (annotation index when there is no instance id).

    Without ``calib``, ``tracking`` and ``camera`` (a camera name) use the camera calibration of
    the export instead (slot ``metadata.cameras`` and per-frame ``camera_from_world``): the camera
    frame of that frame's image with ``P2 = [K | 0]`` (``tracking`` alone picks the first
    calibrated pinhole camera, ``front`` first). An explicit ``calib`` wins.
    """
    output_dir = Path(output_dir)
    for af in annotation_files:
        slot = pointcloud_slot(af)
        if slot is None:
            continue
        cal = _calib_for(calib, af.filename)
        cam = None
        if calib is None and (tracking or camera is not None):
            cam = _export_camera(slot.metadata, camera)
        if (tracking or calib is not None or camera is not None) and not (cal or cam):
            print(f"[WARNING] no KITTI calib for '{af.filename}', skipped")
            continue
        objects = frame_objects(af, ("cuboid_3d",))
        n = slot.frame_count or (max(objects, default=-1) + 1)
        index = {id(a): k for k, a in enumerate(af.annotations)}
        lines: Dict[int, List[str]] = {f: [] for f in range(n)}
        missing_pose = False
        for f, objs in objects.items():
            ego = g.ego_pose_of(slot.metadata, f)
            if (slot.metadata or {}).get("coordinate_frame") == "world" and ego is None:
                missing_pose = True
                break
            fcal = _export_calib(slot.metadata, f, cam) if cam else cal
            if cam and fcal is None:
                print(
                    f"[WARNING] '{af.filename}' frame {f}: no '{cam}' calibration, skipped"
                )
                continue
            size = image_size or (fcal.image_size if fcal else None)
            for o in objs:
                box = o.data if ego is None else g.to_ego_frame(o.data, ego)
                cls = o.annotation.annotation_class.name.replace(" ", "_")
                if fcal is None:
                    lines.setdefault(f, []).append(openpcdet_line(box, cls))
                elif tracking:
                    iid = o.instance_id
                    tid = iid - 1 if iid is not None else index[id(o.annotation)]
                    lines.setdefault(f, []).append(
                        f"{f} {tid} {kitti_line(box, cls, fcal, size)}"
                    )
                else:
                    lines.setdefault(f, []).append(kitti_line(box, cls, fcal, size))
        if missing_pose:
            print(
                f"[WARNING] '{af.filename}' is in the world frame without ego poses, skipped"
            )
            continue
        stem = item_stem(af.filename)
        if tracking:
            output_dir.mkdir(parents=True, exist_ok=True)
            body = [line for f in sorted(lines) for line in lines[f]]
            (output_dir / f"{stem}.txt").write_text("".join(f"{x}\n" for x in body))
        elif (cal or cam) and n == 1:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / f"{stem}.txt").write_text("".join(f"{x}\n" for x in lines[0]))
        else:
            (output_dir / stem).mkdir(parents=True, exist_ok=True)
            for f, body in lines.items():
                (output_dir / stem / f"{f:06d}.txt").write_text(
                    "".join(f"{x}\n" for x in body)
                )
