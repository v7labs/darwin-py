import numpy as np
import pytest

from darwin.exporter import get_exporter
from darwin.importer import get_importer
from darwin.lidar import geometry as g
from darwin.lidar.darwin_json import write_darwin_json
from darwin.lidar.scene import read_scene
from darwin.utils import parse_darwin_json

pa = pytest.importorskip("pyarrow")
feather = pytest.importorskip("pyarrow.feather")

T0 = 315967376859506000
TS = [T0, T0 + 100_000_000]
CAM = "ring_front_center"
K = np.array([[30.0, 0, 20], [0, 30, 15], [0, 0, 1]])
# camera z forward = ego x, camera x right = ego -y, camera y down = ego -z
EGO_FROM_CAM = g.make_pose(
    np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0.0]]), (1.5, 0, 1.6)
)


def _write(path, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    feather.write_feather(pa.table(columns), str(path))


def _pose_columns(poses):
    q = np.array([g.rot_to_quat(p) for p in poses])
    t = np.array([p[:3, 3] for p in poses])
    return {
        "qw": q[:, 0],
        "qx": q[:, 1],
        "qy": q[:, 2],
        "qz": q[:, 3],
        "tx_m": t[:, 0],
        "ty_m": t[:, 1],
        "tz_m": t[:, 2],
    }


def _city_from_ego(t):
    k = (t - T0) / 1e8
    return g.make_pose(
        g.euler_to_rot(0.01, -0.02, 0.5 + 0.1 * k), (1000 + 3 * k, 2000, 30)
    )


@pytest.fixture
def log(tmp_path):
    d = tmp_path / "log-0001"
    rng = np.random.default_rng(0)
    pose_ts = [T0 - 1_000_000, T0, T0 + 2_000_000, TS[1], TS[1] + 3_000_000]
    _write(
        d / "city_SE3_egovehicle.feather",
        {
            "timestamp_ns": pose_ts,
            **_pose_columns([_city_from_ego(t) for t in pose_ts]),
        },
    )
    for t in TS:
        n = 30
        _write(
            d / "sensors" / "lidar" / f"{t}.feather",
            {
                "x": rng.uniform(-40, 40, n).astype("f4"),
                "y": rng.uniform(-40, 40, n).astype("f4"),
                "z": rng.uniform(-2, 3, n).astype("f4"),
                "intensity": rng.integers(0, 255, n).astype("u1"),
                "laser_number": np.zeros(n, "u1"),
                "offset_ns": np.zeros(n, "u4"),
            },
        )
    _write(
        d / "calibration" / "egovehicle_SE3_sensor.feather",
        {"sensor_name": [CAM, "up_lidar"], **_pose_columns([EGO_FROM_CAM, np.eye(4)])},
    )
    _write(
        d / "calibration" / "intrinsics.feather",
        {
            "sensor_name": [CAM],
            "fx_px": [K[0, 0]],
            "fy_px": [K[1, 1]],
            "cx_px": [K[0, 2]],
            "cy_px": [K[1, 2]],
            "k1": [0.0],
            "k2": [0.0],
            "k3": [0.0],
            "height_px": [30],
            "width_px": [40],
        },
    )
    from PIL import Image

    for t in (T0 + 2_000_000, TS[1] + 3_000_000):
        p = d / "sensors" / "cameras" / CAM / f"{t}.jpg"
        p.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (40, 30), (200, 10, 10)).save(p)
    boxes = [
        ("a", TS[0], g.make_pose(g.euler_to_rot(0.0, 0.0, 0.3), (10, 2, 0.5))),
        ("a", TS[1], g.make_pose(g.euler_to_rot(0.0, 0.01, 0.35), (11, 2, 0.5))),
        ("b", TS[1], g.make_pose(g.euler_to_rot(0.0, 0.0, -2.0), (-5, 7, 0.8))),
    ]
    _write(
        d / "annotations.feather",
        {
            "timestamp_ns": [b[1] for b in boxes],
            "track_uuid": [b[0] for b in boxes],
            "category": ["REGULAR_VEHICLE", "REGULAR_VEHICLE", "PEDESTRIAN"],
            "length_m": [4.5, 4.5, 0.6],
            "width_m": [1.9, 1.9, 0.6],
            "height_m": [1.6, 1.6, 1.8],
            **_pose_columns([b[2] for b in boxes]),
            "num_interior_pts": [10, 12, 3],
        },
    )
    return d


def test_build_av2(log, tmp_path, check_calibration):
    from darwin.lidar.av2 import build_av2

    scene = read_scene(build_av2(log, tmp_path / "out"))
    assert scene.path.name == "log-0001.lidar.zip"
    m = scene.manifest
    assert m["coordinate_frame"] == "world" and m["frame_count"] == 2
    assert m["origin"] == pytest.approx(_city_from_ego(T0)[:3, 3].tolist())
    cam = check_calibration(m)[CAM]
    assert cam["distortion"] == {"model": "pinhole"}
    assert cam["intrinsics"]["fx"] == pytest.approx(30 * cam["width"] / 40)
    assert m["cameras"][0]["name"] == CAM and m["cameras"][0]["width"] == 20
    assert [f["timestamp"] for f in m["frames"]] == pytest.approx([0, 0.1])
    origin = _city_from_ego(T0)[:3, 3]
    for i, t in enumerate(TS):
        ego = scene.ego_pose(i)
        expected = g.translation(-origin) @ _city_from_ego(t)
        assert np.allclose(ego, expected, atol=1e-6)
        sweep = feather.read_table(str(log / "sensors" / "lidar" / f"{t}.feather"))
        xyz = np.stack([sweep[k].to_numpy() for k in "xyz"], 1).astype(float)
        assert (
            np.abs(scene.points(i).xyz - g.transform_points(expected, xyz)).max()
            < 0.006
        )
    # a point 10 m ahead of the camera projects to the principal point of the frame-0 image
    img_pose = _city_from_ego(T0 + 2_000_000)
    city_point = g.transform_points(img_pose @ EGO_FROM_CAM, np.array([[0, 0, 10.0]]))[
        0
    ]
    scene_point = city_point - origin
    w2i = np.array(m["frames"][0]["images"][CAM]["world_to_image"])
    u, v, w = w2i @ np.r_[scene_point, 1]
    sx, sy = 20 / 40, m["cameras"][0]["height"] / 30
    assert w > 0 and np.allclose([u / w, v / w], [20 * sx, 15 * sy], atol=1e-3)


def _rows(path):
    t = feather.read_table(str(path)).to_pydict()
    return [dict(zip(t, r)) for r in zip(*t.values())]


def test_av2_import_darwin_json_export_round_trip(log, tmp_path):
    from darwin.lidar.av2 import export_av2, parse_av2

    [af] = parse_av2(log / "annotations.feather")
    assert af.filename == "log-0001.lidar.zip"
    assert [a.annotation_class.name for a in af.annotations] == [
        "REGULAR_VEHICLE",
        "PEDESTRIAN",
    ]
    assert [sorted(a.frames) for a in af.annotations] == [[0, 1], [1]]
    assert [a.frames[1].get_sub("instance_id").data for a in af.annotations] == [1, 2]
    origin = _city_from_ego(T0)[:3, 3]
    scene_box = af.annotations[0].frames[0].data
    expected = (
        g.translation(-origin)
        @ _city_from_ego(T0)
        @ g.make_pose(g.euler_to_rot(0, 0, 0.3), (10, 2, 0.5))
    )
    assert np.allclose(g.cuboid_to_pose(scene_box), expected, atol=1e-9)

    parsed = parse_darwin_json(write_darwin_json(af, tmp_path / "json"))
    export_av2([parsed], tmp_path / "export", log_dir=log)
    original = _rows(log / "annotations.feather")
    exported = _rows(tmp_path / "export" / "log-0001" / "annotations.feather")
    assert len(exported) == len(original)
    uuids = {}
    for o, e in zip(
        sorted(original, key=lambda r: (r["timestamp_ns"], r["category"])),
        sorted(exported, key=lambda r: (r["timestamp_ns"], r["category"])),
    ):
        assert e["timestamp_ns"] == o["timestamp_ns"] and e["category"] == o["category"]
        assert uuids.setdefault(o["track_uuid"], e["track_uuid"]) == e["track_uuid"]
        for k in ("length_m", "width_m", "height_m", "tx_m", "ty_m", "tz_m"):
            assert e[k] == pytest.approx(o[k], abs=1e-6)
        qo = np.array([o[k] for k in ("qw", "qx", "qy", "qz")])
        qe = np.array([e[k] for k in ("qw", "qx", "qy", "qz")])
        assert np.allclose(qo * np.sign(qo @ qe), qe, atol=1e-6)
    assert len(set(uuids.values())) == 2

    get_exporter("argoverse2")([parsed], tmp_path / "rel")
    rel = _rows(tmp_path / "rel" / "log-0001" / "annotations.feather")
    assert sorted({r["timestamp_ns"] for r in rel}) == [0, 100_000_000]


def test_registered_importer(log, tmp_path):
    importer = get_importer("argoverse2")
    assert importer(tmp_path / "x.json") is None
    [af] = importer(log / "annotations.feather")
    assert af.slots[0].metadata["coordinate_frame"] == "world"
    assert len(af.slots[0].metadata["frames"]) == 2


def test_export_writes_calibration_from_the_export(
    log, tmp_path, with_package_calibration
):
    from darwin.lidar.av2 import build_av2, export_av2, parse_av2

    manifest = read_scene(build_av2(log, tmp_path / "pkg")).manifest
    [af] = parse_av2(log)
    calibrated = parse_darwin_json(
        write_darwin_json(with_package_calibration(af, manifest), tmp_path / "json")
    )
    export_av2([calibrated], tmp_path / "export")
    out = tmp_path / "export" / "log-0001" / "calibration"
    [intr] = _rows(out / "intrinsics.feather")
    h = manifest["cameras"][0]["height"]
    assert intr == pytest.approx(
        {
            "sensor_name": CAM,
            "fx_px": 15.0,
            "fy_px": 30 * h / 30,
            "cx_px": 10.0,
            "cy_px": 15 * h / 30,
            "k1": 0.0,
            "k2": 0.0,
            "k3": 0.0,
            "height_px": h,
            "width_px": 20,
        }
    )
    [extr] = _rows(out / "egovehicle_SE3_sensor.feather")
    ego_from_cam = g.make_pose(
        g.quat_to_rot(*(extr[k] for k in ("qw", "qx", "qy", "qz"))),
        [extr[k] for k in ("tx_m", "ty_m", "tz_m")],
    )
    # the first image is 2 ms after the sweep: its camera pose in the sweep's ego frame
    expected = (
        g.invert(_city_from_ego(T0)) @ _city_from_ego(T0 + 2_000_000) @ EGO_FROM_CAM
    )
    assert np.allclose(ego_from_cam, expected, atol=1e-5)
    export_av2([af], tmp_path / "plain")
    assert not (tmp_path / "plain" / "log-0001" / "calibration").exists()
