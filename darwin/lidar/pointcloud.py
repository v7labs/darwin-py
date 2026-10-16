"""
Point cloud readers/writers. Every reader keeps the file's point order, because ``point_mask_3d``
annotations index points in file order.

Supported: ``.pcd`` (ascii / binary / binary_compressed), ``.bin`` (KITTI float32 x y z
intensity), ``.pcd.bin`` (nuScenes float32 x y z intensity ring), ``.ply`` (ascii / binary),
``.npy`` (``(N, >=3)`` or structured with x/y/z), ``.las`` / ``.laz`` (needs ``laspy``) and
``.feather`` (Argoverse 2 sweeps, needs ``pyarrow``).
"""

import struct
from pathlib import Path
from typing import NamedTuple, Optional, Union

import numpy as np

PathLike = Union[str, Path]
INTENSITY_NAMES = ("intensity", "i", "reflectance", "remission", "intensities")


class PointCloud(NamedTuple):
    #: ``(N, 3)`` float64 coordinates.
    xyz: np.ndarray
    #: ``(N,)`` intensity in the file's own scale, or ``None``.
    intensity: Optional[np.ndarray] = None


def missing_dependency(package: str, extra: str) -> ImportError:
    return ImportError(
        f"'{package}' is required for this format. Install it with "
        f"`pip install darwin-py[{extra}]` (or `pip install {package}`)."
    )


def intensity_u8(intensity: Optional[np.ndarray]) -> Optional[np.ndarray]:
    """
    Intensity as 0-255 ``uint8``: ``[0, 1]`` clouds are scaled by 255, clouds above 255 are taken
    as 16-bit (LAS, Ouster) and divided by 257, others are kept.
    """
    if intensity is None:
        return None
    i = np.nan_to_num(np.asarray(intensity, float))
    peak = i.max() if len(i) else 0
    if peak <= 1.0:
        i = i * 255
    elif peak > 255:
        i = i / 257
    return np.clip(np.round(i), 0, 255).astype(np.uint8)


# --- PCD ------------------------------------------------------------------------------------

_PCD_TYPES = {"F": "f", "U": "u", "I": "i"}


def _lzf_decompress(data: bytes, size: int) -> bytes:
    # ponytail: pure-Python LZF, ~seconds for millions of points; swap in a C codec if it matters
    out = bytearray(size)
    i = o = 0
    while i < len(data):
        ctrl = data[i]
        i += 1
        if ctrl < 32:
            n = ctrl + 1
            out[o : o + n] = data[i : i + n]
            i += n
            o += n
            continue
        n = ctrl >> 5
        if n == 7:
            n += data[i]
            i += 1
        ref = o - ((ctrl & 0x1F) << 8) - data[i] - 1
        i += 1
        n += 2
        if ref + n <= o:
            out[o : o + n] = out[ref : ref + n]
        else:
            for k in range(n):
                out[o + k] = out[ref + k]
        o += n
    if o != size:
        raise ValueError("PCD: corrupt binary_compressed data")
    return bytes(out)


def read_pcd(source: Union[PathLike, bytes]) -> PointCloud:
    """Reads a PCD v0.5-0.7 file (``DATA ascii``, ``binary`` or ``binary_compressed``)."""
    raw = source if isinstance(source, bytes) else Path(source).read_bytes()
    header, pos = {}, 0
    while True:
        end = raw.index(b"\n", pos)
        line = raw[pos:end].decode("ascii", "replace").strip()
        pos = end + 1
        if not line or line.startswith("#"):
            continue
        key, *values = line.split()
        header[key.upper()] = values
        if key.upper() == "DATA":
            break
    names = header["FIELDS"]
    sizes = [int(s) for s in header.get("SIZE", ["4"] * len(names))]
    types = header.get("TYPE", ["F"] * len(names))
    counts = [int(c) for c in header.get("COUNT", ["1"] * len(names))]
    n = (
        int(header["POINTS"][0])
        if "POINTS" in header
        else int(header["WIDTH"][0]) * int(header["HEIGHT"][0])
    )
    fields = [
        (f"{name}__{k}", f"<{_PCD_TYPES[t.upper()]}{s}", (c,) if c > 1 else ())
        for k, (name, s, t, c) in enumerate(zip(names, sizes, types, counts))
    ]
    dtype = np.dtype(fields)
    encoding = header["DATA"][0].lower()
    body = raw[pos:]
    if encoding == "ascii":
        values = np.array(body.split()[: n * sum(counts)], dtype=float).reshape(n, -1)
        offsets = np.cumsum([0] + counts)
        columns = {name: values[:, offsets[k]] for k, name in enumerate(names)}
    else:
        if encoding == "binary":
            arr = np.frombuffer(body, dtype, count=n)
            columns = {name: arr[f[0]] for name, f in zip(names, fields)}
        elif encoding == "binary_compressed":
            csize, usize = struct.unpack("<II", body[:8])
            data = _lzf_decompress(body[8 : 8 + csize], usize)
            columns, off = {}, 0
            for name, (_, fmt, shape) in zip(names, fields):
                item = np.dtype((fmt, shape))
                columns[name] = np.frombuffer(data, item, count=n, offset=off)
                off += item.itemsize * n
        else:
            raise ValueError(f"PCD: unsupported DATA encoding '{encoding}'")
    xyz = np.stack([np.asarray(columns[k], float).reshape(n) for k in "xyz"], 1)
    name = next((k for k in INTENSITY_NAMES if k in columns), None)
    return PointCloud(
        xyz, None if name is None else np.asarray(columns[name], float).reshape(n)
    )


def pcd_bytes(
    xyz: np.ndarray,
    intensity: Optional[np.ndarray] = None,
    scale: Optional[float] = None,
    offset: Optional[np.ndarray] = None,
) -> bytes:
    """
    Binary PCD with ``x y z`` (``F 4``, or ``I 2`` quantized as ``raw * scale + offset`` when
    ``scale`` is given) and an optional ``intensity`` (``U 1``, see :func:`intensity_u8`).
    """
    xyz = np.asarray(xyz, float)
    xyz_type = ("<i2", "I", 2) if scale else ("<f4", "F", 4)
    fields = [("x", xyz_type[0]), ("y", xyz_type[0]), ("z", xyz_type[0])]
    inten = intensity_u8(intensity)
    if inten is not None:
        fields.append(("intensity", "u1"))
    rec = np.empty(len(xyz), dtype=fields)
    values = (
        xyz
        if not scale
        else np.round((xyz - np.asarray(offset if offset is not None else 0.0)) / scale)
    )
    rec["x"], rec["y"], rec["z"] = values.T
    if inten is not None:
        rec["intensity"] = inten
    names = "x y z" + (" intensity" if inten is not None else "")
    sizes = " ".join([str(xyz_type[2])] * 3 + (["1"] if inten is not None else []))
    kinds = " ".join([xyz_type[1]] * 3 + (["U"] if inten is not None else []))
    counts = " ".join(["1"] * len(fields))
    header = (
        "# .PCD v0.7 - Point Cloud Data file format\nVERSION 0.7\n"
        f"FIELDS {names}\nSIZE {sizes}\nTYPE {kinds}\nCOUNT {counts}\n"
        f"WIDTH {len(rec)}\nHEIGHT 1\nVIEWPOINT 0 0 0 1 0 0 0\nPOINTS {len(rec)}\nDATA binary\n"
    )
    return header.encode("ascii") + rec.tobytes()


def write_pcd(
    path: PathLike, xyz: np.ndarray, intensity: Optional[np.ndarray] = None
) -> Path:
    """Writes a float32 binary PCD, the format Darwin accepts as a single-frame point cloud."""
    path = Path(path)
    path.write_bytes(pcd_bytes(xyz, intensity))
    return path


# --- PLY ------------------------------------------------------------------------------------

_PLY_TYPES = {
    "char": "i1", "int8": "i1", "uchar": "u1", "uint8": "u1",
    "short": "i2", "int16": "i2", "ushort": "u2", "uint16": "u2",
    "int": "i4", "int32": "i4", "uint": "u4", "uint32": "u4",
    "float": "f4", "float32": "f4", "double": "f8", "float64": "f8",
}  # fmt: skip


def read_ply(path: PathLike) -> PointCloud:
    """Reads the ``vertex`` element of an ascii / binary PLY (vertex must be the first element)."""
    raw = Path(path).read_bytes()
    end = raw.index(b"end_header") + len(b"end_header")
    end = raw.index(b"\n", end) + 1
    lines = raw[:end].decode("ascii").splitlines()
    fmt = next(line.split()[1] for line in lines if line.startswith("format"))
    elements = [
        line.split() for line in lines if line.startswith(("element", "property"))
    ]
    if not elements or elements[0][:2] != ["element", "vertex"]:
        raise ValueError("PLY: the first element must be 'vertex'")
    n = int(elements[0][2])
    props = []
    for e in elements[1:]:
        if e[0] == "element":
            break
        if e[1] == "list":
            raise ValueError("PLY: list properties on vertices are not supported")
        props.append((e[2], _PLY_TYPES[e[1]]))
    if fmt == "ascii":
        values = np.array(raw[end:].split()[: n * len(props)], float).reshape(
            n, len(props)
        )
        cols = {name: values[:, k] for k, (name, _) in enumerate(props)}
    else:
        order = "<" if fmt == "binary_little_endian" else ">"
        arr = np.frombuffer(
            raw, np.dtype([(p, order + t) for p, t in props]), count=n, offset=end
        )
        cols = {name: arr[name] for name, _ in props}
    name = next((k for k in INTENSITY_NAMES + ("scalar_intensity",) if k in cols), None)
    xyz = np.stack([np.asarray(cols[k], float) for k in "xyz"], 1)
    return PointCloud(xyz, None if name is None else np.asarray(cols[name], float))


# --- other formats --------------------------------------------------------------------------


def read_bin(path: PathLike, columns: int = 4) -> PointCloud:
    """float32 records (KITTI: 4 columns x y z reflectance, nuScenes ``.pcd.bin``: 5 columns)."""
    a = np.fromfile(path, dtype="<f4").reshape(-1, columns)
    return PointCloud(
        a[:, :3].astype(float), a[:, 3].astype(float) if columns > 3 else None
    )


def read_npy(path: PathLike) -> PointCloud:
    a = np.load(path, allow_pickle=False)
    if a.dtype.names:
        xyz = np.stack([a[k].astype(float) for k in "xyz"], 1)
        name = next((k for k in INTENSITY_NAMES if k in a.dtype.names), None)
        return PointCloud(xyz, None if name is None else a[name].astype(float))
    a = np.asarray(a, float).reshape(len(a), -1)
    return PointCloud(a[:, :3], a[:, 3] if a.shape[1] > 3 else None)


def read_las(path: PathLike) -> PointCloud:
    try:
        import laspy
    except ImportError:
        raise missing_dependency("laspy", "lidar_las") from None
    las = laspy.read(str(path))
    xyz = np.stack([np.asarray(las.x), np.asarray(las.y), np.asarray(las.z)], 1).astype(
        float
    )
    return PointCloud(xyz, np.asarray(las.intensity, float))


def read_feather(path: PathLike) -> PointCloud:
    """Argoverse 2 lidar sweep (columns x, y, z, intensity, ...)."""
    try:
        import pyarrow.feather as feather
    except ImportError:
        raise missing_dependency("pyarrow", "lidar_av2") from None
    t = feather.read_table(str(path))
    xyz = np.stack([t[k].to_numpy().astype(float) for k in "xyz"], 1)
    inten = (
        t["intensity"].to_numpy().astype(float)
        if "intensity" in t.column_names
        else None
    )
    return PointCloud(xyz, inten)


def read_points(path: PathLike) -> PointCloud:
    """Reads any supported point cloud file, picking the reader from the file name."""
    name = Path(path).name.lower()
    if name.endswith(".pcd.bin"):
        return read_bin(path, 5)
    readers = {
        ".pcd": read_pcd,
        ".bin": read_bin,
        ".ply": read_ply,
        ".npy": read_npy,
        ".las": read_las,
        ".laz": read_las,
        ".feather": read_feather,
    }
    reader = readers.get(Path(name).suffix)
    if reader is None:
        raise ValueError(f"Unsupported point cloud file: {path}")
    return reader(path)
