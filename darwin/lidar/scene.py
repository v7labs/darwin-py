"""
Writer/reader for ``darwin-lidar-scene`` v2 packages (``.lidar.zip``), the multi-frame LiDAR +
multi-camera upload format of Darwin.

Layout: ``scene.json`` (STORED, first entry), ``thumbnail.jpg``, ``lidar/000000.pcd`` (DEFLATE),
``cameras/<camera>/000000.jpg`` (STORED). No zip64.
"""

import io
import json
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

from darwin.lidar.pointcloud import (
    PathLike,
    PointCloud,
    intensity_u8,
    pcd_bytes,
    read_pcd,
)

SCALE = 0.01
INT16_REACH = 32767 * SCALE


@dataclass
class CameraImage:
    #: Image file, encoded bytes or a ``PIL.Image``.
    image: Any
    #: 3x4 ``K @ camera_from_scene`` for this image, in the pixel coordinates of ``image``.
    world_to_image: np.ndarray


@dataclass
class Frame:
    #: ``(N, 3)`` points in the scene frame (file order is kept).
    points: np.ndarray
    intensity: Optional[np.ndarray] = None
    #: Seconds (any origin; stored relative to the first frame).
    timestamp: float = 0.0
    #: 4x4 ``scene_from_ego`` at the sweep; required for ``coordinate_frame="world"``.
    ego_pose: Optional[np.ndarray] = None
    images: Dict[str, CameraImage] = field(default_factory=dict)


def _jpeg(image: Any, scale: float, quality: int) -> tuple:
    from PIL import Image

    if (
        scale == 1
        and isinstance(image, (str, Path))
        and Path(image).suffix.lower() in (".jpg", ".jpeg")
    ):
        data = Path(image).read_bytes()
        with Image.open(io.BytesIO(data)) as im:
            return data, im.size, im.size
    if isinstance(image, (str, Path)):
        im = Image.open(image)
    elif isinstance(image, bytes):
        im = Image.open(io.BytesIO(image))
    else:
        im = image
    src = im.size
    im = im.convert("RGB")
    if scale != 1:
        size = (
            max(2, int(round(src[0] * scale / 2) * 2)),
            max(2, int(round(src[1] * scale / 2) * 2)),
        )
        im = im.resize(size, Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality)
    return buf.getvalue(), src, im.size


def _height_colors(z: np.ndarray) -> np.ndarray:
    t = np.clip((z + 2.5) / 4.5, 0, 1)
    rgb = [np.clip(1.5 - np.abs(4 * t - c), 0, 1) for c in (3, 2, 1)]
    return (np.stack(rgb, 1) * 255).astype(np.uint8)


def bev_thumbnail(
    points: np.ndarray, center: np.ndarray, w: int = 512, h: int = 384, ppm: float = 6.4
) -> bytes:
    """Height-colored top view (x right, y up) around ``center``, as JPEG."""
    from PIL import Image

    img = np.full((h, w, 3), 18, np.uint8)
    pts = points[np.isfinite(points).all(1)]
    cols = (w / 2 + (pts[:, 0] - center[0]) * ppm).astype(int)
    rows = (h / 2 - (pts[:, 1] - center[1]) * ppm).astype(int)
    m = (cols >= 0) & (cols < w) & (rows >= 0) & (rows < h)
    order = np.argsort(pts[m, 2])
    img[rows[m][order], cols[m][order]] = _height_colors(pts[m, 2][order] - center[2])
    buf = io.BytesIO()
    Image.fromarray(img).save(buf, "JPEG", quality=88)
    return buf.getvalue()


def write_scene(
    path: PathLike,
    frames: Iterable[Frame],
    name: Optional[str] = None,
    fps: float = 10,
    coordinate_frame: str = "world",
    image_scale: float = 0.5,
    jpeg_quality: int = 85,
    quantize: bool = True,
) -> Path:
    """
    Writes a v2 ``.lidar.zip``. ``frames`` may be a generator: frames are spooled to a temporary
    directory, so memory stays at about one frame.

    Points are stored as int16 with 1 cm resolution (``points.scale``) around a per-frame offset
    when every frame fits in that range and has only finite values; otherwise as float32.
    Images are re-encoded as JPEG scaled by ``image_scale`` (JPEG sources at scale 1 are copied).
    """
    if coordinate_frame not in ("world", "sensor"):
        raise ValueError("coordinate_frame must be 'world' or 'sensor'")
    path = Path(path)
    with tempfile.TemporaryDirectory(dir=path.parent) as tmp:
        tmp = Path(tmp)
        manifest: List[Dict[str, Any]] = []
        cameras: Dict[str, Dict[str, Any]] = {}
        fits, thumb, t0 = True, None, None
        for i, frame in enumerate(frames):
            xyz = np.asarray(frame.points, float).reshape(-1, 3)
            inten = intensity_u8(frame.intensity)
            finite = np.isfinite(xyz).all()
            center = (
                (xyz.min(0) + xyz.max(0)) / 2 if len(xyz) and finite else np.zeros(3)
            )
            offset = np.round(center, 2)
            fits = (
                fits
                and bool(finite)
                and (len(xyz) == 0 or np.abs(xyz - offset).max() < INT16_REACH - 1)
            )
            np.save(tmp / f"{i}.npy", xyz)
            if inten is not None:
                np.save(tmp / f"{i}.i.npy", inten)
            t0 = frame.timestamp if t0 is None else t0
            entry: Dict[str, Any] = {
                "timestamp": round(float(frame.timestamp - t0), 6),
                "lidar": f"lidar/{i:06d}.pcd",
                "offset": offset.tolist(),
            }
            if frame.ego_pose is not None:
                entry["ego_pose"] = np.round(
                    np.asarray(frame.ego_pose, float), 6
                ).tolist()
            elif coordinate_frame == "world":
                raise ValueError(
                    f"frame {i}: ego_pose is required for a world-frame scene"
                )
            images = {}
            for cam, ci in frame.images.items():
                data, src, dst = _jpeg(ci.image, image_scale, jpeg_quality)
                rel = f"cameras/{cam}/{i:06d}.jpg"
                (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
                (tmp / rel).write_bytes(data)
                m = np.diag([dst[0] / src[0], dst[1] / src[1], 1.0]) @ np.asarray(
                    ci.world_to_image, float
                )
                images[cam] = {"path": rel, "world_to_image": np.round(m, 6).tolist()}
                cameras.setdefault(
                    cam, {"name": cam, "width": dst[0], "height": dst[1]}
                )
            if images:
                entry["images"] = images
            manifest.append(entry)
            if thumb is None:
                c = (
                    np.asarray(frame.ego_pose, float)[:3, 3]
                    if frame.ego_pose is not None
                    else np.zeros(3)
                )
                thumb = bev_thumbnail(xyz, c)
        if not manifest:
            raise ValueError("A scene needs at least one frame")
        scale = SCALE if quantize and fits else None
        scene: Dict[str, Any] = {
            "format": "darwin-lidar-scene",
            "version": 2,
            "name": name or path.name.split(".")[0],
            "fps": fps,
            "frame_count": len(manifest),
            "coordinate_frame": coordinate_frame,
        }
        if scale:
            scene["points"] = {"scale": scale}
        else:
            for entry in manifest:
                entry.pop("offset")
        scene["cameras"] = list(cameras.values())
        scene["frames"] = manifest
        with zipfile.ZipFile(path, "w", allowZip64=False) as z:
            z.writestr(
                "scene.json", json.dumps(scene), compress_type=zipfile.ZIP_STORED
            )
            z.writestr("thumbnail.jpg", thumb, compress_type=zipfile.ZIP_STORED)
            for i, entry in enumerate(manifest):
                xyz = np.load(tmp / f"{i}.npy")
                ipath = tmp / f"{i}.i.npy"
                inten = np.load(ipath) if ipath.exists() else None
                off = np.asarray(entry.get("offset", [0, 0, 0]))
                z.writestr(
                    entry["lidar"],
                    pcd_bytes(xyz, inten, scale, off),
                    compress_type=zipfile.ZIP_DEFLATED,
                    compresslevel=6,
                )
            for entry in manifest:
                for image in entry.get("images", {}).values():
                    z.write(
                        tmp / image["path"],
                        image["path"],
                        compress_type=zipfile.ZIP_STORED,
                    )
    return path


class Scene:
    """Read access to a ``.lidar.zip`` (v1 or v2): ``manifest`` and per-frame points."""

    def __init__(self, path: PathLike):
        self.path = Path(path)
        self._zip = zipfile.ZipFile(self.path)
        self.manifest: Dict[str, Any] = json.loads(self._zip.read("scene.json"))
        self.frames: List[Dict[str, Any]] = self.manifest.get("frames") or [
            {"lidar": f} for f in self.manifest.get("lidar", {}).get("frames", [])
        ]

    def __len__(self) -> int:
        return len(self.frames)

    def points(self, i: int) -> PointCloud:
        """Points of frame ``i`` in the scene frame (dequantized)."""
        cloud = read_pcd(self._zip.read(self.frames[i]["lidar"]))
        scale = (self.manifest.get("points") or {}).get("scale")
        if scale:
            off = np.asarray(self.frames[i].get("offset", [0, 0, 0]), float)
            return PointCloud(cloud.xyz * scale + off, cloud.intensity)
        return cloud

    def ego_pose(self, i: int) -> Optional[np.ndarray]:
        pose = self.frames[i].get("ego_pose")
        return None if pose is None else np.asarray(pose, float)

    def read(self, name: str) -> bytes:
        return self._zip.read(name)

    def close(self) -> None:
        self._zip.close()


def read_scene(path: PathLike) -> Scene:
    return Scene(path)


def package_path(output: PathLike, name: str) -> Path:
    """``output`` itself when it ends with ``.lidar.zip``, else ``output/<name>.lidar.zip``."""
    output = Path(output)
    if output.name.endswith(".lidar.zip"):
        output.parent.mkdir(parents=True, exist_ok=True)
        return output
    output.mkdir(parents=True, exist_ok=True)
    return output / f"{name}.lidar.zip"
