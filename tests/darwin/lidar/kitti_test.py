import numpy as np
import pytest
from PIL import Image

from darwin.exporter import get_exporter
from darwin.importer import get_importer
from darwin.lidar import geometry as g
from darwin.lidar.darwin_json import frame_objects, write_darwin_json
from darwin.lidar.kitti import (
    build_kitti_object,
    build_kitti_raw,
    build_kitti_tracking,
    export_kitti,
    load_calib,
    parse_kitti_labels,
    parse_kitti_tracking,
    parse_kitti_tracklets,
)
from darwin.lidar.scene import read_scene
from darwin.utils import parse_darwin_json

# real KITTI 2011_09_26 calibration values
P2 = "7.215377e+02 0.000000e+00 6.095593e+02 4.485728e+01 0.000000e+00 7.215377e+02 1.728540e+02 2.163791e-01 0.000000e+00 0.000000e+00 1.000000e+00 2.745884e-03"
R0 = "9.999239e-01 9.837760e-03 -7.445048e-03 -9.869795e-03 9.999421e-01 -4.278459e-03 7.402527e-03 4.351614e-03 9.999631e-01"
TR = "7.533745e-03 -9.999714e-01 -6.166020e-04 -4.069766e-03 1.480249e-02 7.280733e-04 -9.998902e-01 -7.631618e-02 9.998621e-01 7.523790e-03 1.480755e-02 -2.717806e-01"
IMU = "9.999976e-01 7.553071e-04 -2.035826e-03 -8.086759e-01 -7.854027e-04 9.998898e-01 -1.482298e-02 3.195559e-01 2.024406e-03 1.482454e-02 9.998881e-01 -7.997231e-01"
OBJECT_CALIB = f"P0: {P2}\nP1: {P2}\nP2: {P2}\nP3: {P2}\nR0_rect: {R0}\nTr_velo_to_cam: {TR}\nTr_imu_to_velo: {IMU}\n"
TRACKING_CALIB = f"P0: {P2}\nP1: {P2}\nP2: {P2}\nP3: {P2}\nR_rect {R0}\nTr_velo_cam {TR}\nTr_imu_velo {IMU}\n"

LABEL_2 = """Car 0.00 0 -1.58 587.01 173.33 614.12 200.12 1.65 1.67 3.64 -0.65 1.71 46.70 -1.59
Pedestrian 0.00 0 0.21 423.17 173.67 433.17 224.03 1.87 0.50 0.90 -5.73 1.78 26.36 0.30
DontCare -1 -1 -10 503.89 169.71 590.61 190.13 -1 -1 -1 -1000 -1000 -1000 -10
"""
LABEL_02 = """0 0 Car 0 0 -1.79 296.74 161.75 455.23 292.50 2.00 1.82 4.43 -4.55 1.65 13.70 -2.10
1 0 Car 0 0 -1.79 296.74 161.75 455.23 292.50 2.00 1.82 4.43 -4.45 1.66 12.90 -2.08
2 0 Car 0 0 -1.79 296.74 161.75 455.23 292.50 2.00 1.82 4.43 -4.35 1.67 12.10 -2.05
1 1 Pedestrian 0 0 0.10 700.00 150.00 720.00 220.00 1.80 0.60 0.80 3.10 1.70 9.00 1.20
2 1 Pedestrian 0 0 0.10 700.00 150.00 720.00 220.00 1.80 0.60 0.80 3.00 1.70 9.20 1.25
1 -1 DontCare -1 -1 -10.00 0 0 10 10 -1 -1 -1 -1000 -1000 -1000 -10
"""


def _oxts(n):
    rows = []
    for i in range(n):
        row = [49.011 + 1e-5 * i, 8.4231 + 2e-5 * i, 112.8, 0.01, -0.02, 0.4 + 0.05 * i]
        rows.append(" ".join(map(str, row + [0.0] * 24)))
    return rows


def _png(path, w=40, h=12):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.full((h, w, 3), 128, np.uint8)).save(path)


def _bin(path, pts):
    path.parent.mkdir(parents=True, exist_ok=True)
    np.c_[pts, np.full(len(pts), 0.5)].astype("<f4").tofile(path)


def _rows(text):
    return [line.split() for line in text.strip().splitlines()]


def _velo_points_in(cuboid, n=30, seed=0):
    rng = np.random.default_rng(seed)
    d = np.array([cuboid["dimensions"][k] for k in "xyz"])
    local = rng.uniform(-0.4, 0.4, (n, 3)) * d
    return g.transform_points(g.cuboid_to_pose(cuboid), local)


@pytest.fixture
def object_root(tmp_path):
    base = tmp_path / "object" / "training"
    (base / "calib").mkdir(parents=True)
    (base / "calib" / "000001.txt").write_text(OBJECT_CALIB)
    (base / "label_2").mkdir()
    (base / "label_2" / "000001.txt").write_text(LABEL_2)
    _bin(
        base / "velodyne" / "000001.bin",
        np.random.default_rng(0).uniform(-30, 30, (100, 3)),
    )
    _png(base / "image_2" / "000001.png")
    return base


@pytest.fixture
def tracking_root(tmp_path):
    base = tmp_path / "tracking" / "training"
    (base / "calib").mkdir(parents=True)
    (base / "calib" / "0000.txt").write_text(TRACKING_CALIB)
    (base / "label_02").mkdir()
    (base / "label_02" / "0000.txt").write_text(LABEL_02)
    (base / "oxts").mkdir()
    (base / "oxts" / "0000.txt").write_text("\n".join(_oxts(3)))
    tracks = parse_kitti_tracking(base / "label_02" / "0000.txt")[0].annotations
    for f in range(3):
        pts = [np.random.default_rng(f).uniform(-30, 30, (50, 3))]
        pts += [
            _velo_points_in(t.frames[f].data, seed=f) for t in tracks if f in t.frames
        ]
        _bin(base / "velodyne" / "0000" / f"{f:06d}.bin", np.concatenate(pts))
        _png(base / "image_02" / "0000" / f"{f:06d}.png")
    return base


def test_camera_to_velo_matches_kitti_devkit_corners(object_root):
    calib = load_calib(object_root / "calib" / "000001.txt")
    af = parse_kitti_labels(object_root / "label_2" / "000001.txt")[0]
    assert af.filename == "kitti_object_training_000001.lidar.zip"
    assert [a.annotation_class.name for a in af.annotations] == ["Car", "Pedestrian"]
    for row, track in zip(_rows(LABEL_2), af.annotations):
        h, w, ln, x, y, z, ry = map(float, row[8:15])
        c, s = np.cos(ry), np.sin(ry)
        rot = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        xs = np.array([ln, ln, -ln, -ln, ln, ln, -ln, -ln]) / 2
        ys = np.array([0, 0, 0, 0, -h, -h, -h, -h])
        zs = np.array([w, -w, -w, w, w, -w, -w, w]) / 2
        cam = (rot @ np.stack([xs, ys, zs])).T + [x, y, z]
        velo = g.transform_points(np.linalg.inv(calib.velo_to_rect), cam)
        ours = g.box_corners(track.frames[0].data)
        assert np.abs(velo[:, None] - ours[None]).sum(-1).min(1).max() < 1e-6
    # standard KITTI relation: velodyne heading = -rotation_y - pi/2 (up to calib tilt)
    car = af.annotations[0].frames[0].data
    assert abs(g.wrap_angle(car["rotation"]["z"] - (1.59 - np.pi / 2))) < 0.02


def test_label_2_round_trip_through_darwin_json(object_root, tmp_path):
    af = parse_kitti_labels(object_root / "label_2" / "000001.txt")[0]
    back = parse_darwin_json(write_darwin_json(af, tmp_path / "json"))
    out = tmp_path / "out"
    export_kitti(
        [back], out, calib=object_root / "calib" / "000001.txt", image_size=(1242, 375)
    )
    exported = _rows((out / "kitti_object_training_000001.txt").read_text())
    original = [r for r in _rows(LABEL_2) if r[0] != "DontCare"]
    assert len(exported) == len(original)
    for e, o in zip(exported, original):
        assert e[0] == o[0]
        assert np.allclose(
            [float(v) for v in e[8:15]], [float(v) for v in o[8:15]], atol=1e-4
        )
        assert 0 <= float(e[4]) < float(e[6]) <= 1241  # projected, clipped 2D box


def test_tracking_round_trip(tracking_root, tmp_path):
    af = parse_kitti_tracking(tracking_root / "label_02" / "0000.txt")[0]
    assert af.filename == "kitti_tracking_training_0000.lidar.zip"
    assert af.slots[0].frame_count == 3
    car, ped = af.annotations
    assert car.segments == [[0, 3]] and ped.segments == [[1, 3]]
    back = parse_darwin_json(write_darwin_json(af, tmp_path / "json"))
    export_kitti(
        [back],
        tmp_path / "out",
        calib=tracking_root / "calib" / "0000.txt",
        tracking=True,
    )
    exported = _rows(
        (tmp_path / "out" / "kitti_tracking_training_0000.txt").read_text()
    )
    original = [r for r in _rows(LABEL_02) if r[2] != "DontCare"]
    key = lambda r: (int(r[0]), int(r[1]))  # noqa: E731
    exported, original = sorted(exported, key=key), sorted(original, key=key)
    assert [key(r) + (r[2],) for r in exported] == [key(r) + (r[2],) for r in original]
    for e, o in zip(exported, original):
        assert np.allclose(
            [float(v) for v in e[10:17]], [float(v) for v in o[10:17]], atol=1e-4
        )


def test_tracking_world_frame_matches_built_scene(tracking_root, tmp_path):
    path = build_kitti_tracking(tracking_root.parent, 0, tmp_path / "pkg", world=True)
    assert path.name == "kitti_tracking_training_0000.lidar.zip"
    scene = read_scene(path)
    assert scene.manifest["coordinate_frame"] == "world" and len(scene) == 3
    assert np.allclose(scene.ego_pose(0)[:3, 3], 0, atol=1e-6)
    af = parse_kitti_tracking(tracking_root / "label_02" / "0000.txt", world=True)[0]
    meta = af.slots[0].metadata
    assert meta["coordinate_frame"] == "world"
    sensor = parse_kitti_tracking(tracking_root / "label_02" / "0000.txt")[0]
    for f in range(3):
        assert np.allclose(meta["frames"][f]["ego_pose"], scene.ego_pose(f), atol=1e-5)
        pts = scene.points(f).xyz
        for track, velo_track in zip(af.annotations, sensor.annotations):
            if f not in track.frames:
                continue
            box = track.frames[f].data
            local = g.transform_points(g.invert(g.cuboid_to_pose(box)), pts)
            half = np.array([box["dimensions"][k] for k in "xyz"]) / 2
            assert (np.abs(local) <= half + 0.01).all(1).sum() == 30
            # ego-frame view of the world box is the velodyne box
            ego_box = g.to_ego_frame(box, scene.ego_pose(f))
            ref = velo_track.frames[f].data
            assert [ego_box["position"][k] for k in "xyz"] == pytest.approx(
                [ref["position"][k] for k in "xyz"], abs=1e-4
            )
    # lidar-frame export of the world-frame item equals the velodyne boxes
    export_kitti([af], tmp_path / "pcdet")
    lines = _rows(
        (tmp_path / "pcdet" / "kitti_tracking_training_0000" / "000001.txt").read_text()
    )
    ref = [t.frames[1].data for t in sensor.annotations]
    assert len(lines) == 2
    for line, box in zip(lines, ref):
        assert np.allclose(
            [float(v) for v in line[:3]], [box["position"][k] for k in "xyz"], atol=1e-4
        )
        assert line[7] in ("Car", "Pedestrian")
    assert (
        tmp_path / "pcdet" / "kitti_tracking_training_0000" / "000000.txt"
    ).read_text().count("\n") == 1


def test_tracking_sensor_build_and_projection(
    tracking_root, tmp_path, check_calibration
):
    scene = read_scene(build_kitti_tracking(tracking_root, "0000", tmp_path))
    assert scene.manifest["coordinate_frame"] == "sensor"
    calib = load_calib(tracking_root / "calib" / "0000.txt")
    [cam] = check_calibration(scene.manifest).values()
    k = 0.5 * calib.P2[:2, :3]
    assert cam == {
        "name": "front",
        "width": 20,
        "height": 6,
        "intrinsics": pytest.approx(
            {"fx": k[0, 0], "fy": k[1, 1], "cx": k[0, 2], "cy": k[1, 2]}
        ),
        "distortion": {"model": "pinhole"},
    }
    assert "origin" not in scene.manifest
    m = np.array(scene.frames[0]["images"]["front"]["world_to_image"])
    assert np.allclose(
        m, np.diag([0.5, 0.5, 1]) @ calib.velo_to_image, rtol=1e-5, atol=1e-5
    )
    raw = np.fromfile(
        tracking_root / "velodyne" / "0000" / "000002.bin", "<f4"
    ).reshape(-1, 4)
    assert (
        np.abs(scene.points(2).xyz - raw[:, :3]).max() <= 0.0051
    )  # every point, file order


def test_raw_drive_builder_and_tracklets(tmp_path):
    date = tmp_path / "2011_09_26"
    drive = date / "2011_09_26_drive_0001_sync"
    tr = np.array(TR.split(), float).reshape(3, 4)
    imu = np.array(IMU.split(), float).reshape(3, 4)
    (date / "calib_velo_to_cam.txt").parent.mkdir(parents=True)
    (date / "calib_velo_to_cam.txt").write_text(
        "calib_time: 15-Mar-2012 11:37:16\nR: "
        + " ".join(map(str, tr[:, :3].ravel()))
        + "\nT: "
        + " ".join(map(str, tr[:, 3]))
        + "\n"
    )
    (date / "calib_imu_to_velo.txt").write_text(
        "calib_time: 25-May-2012 16:47:16\nR: "
        + " ".join(map(str, imu[:, :3].ravel()))
        + "\nT: "
        + " ".join(map(str, imu[:, 3]))
        + "\n"
    )
    (date / "calib_cam_to_cam.txt").write_text(
        f"calib_time: 09-Jan-2012 13:57:47\nS_rect_02: 1.242000e+03 3.750000e+02\nR_rect_00: {R0}\nP_rect_02: {P2}\n"
    )
    stamps = [
        "2011-09-26 13:02:25.964389445",
        "2011-09-26 13:02:26.074389445",
        "2011-09-26 13:02:26.164389445",
    ]
    (drive / "velodyne_points").mkdir(parents=True)
    (drive / "velodyne_points" / "timestamps.txt").write_text("\n".join(stamps) + "\n")
    (drive / "oxts" / "data").mkdir(parents=True)
    for i, row in enumerate(_oxts(3)):
        _bin(
            drive / "velodyne_points" / "data" / f"{i:010d}.bin",
            np.random.default_rng(i).uniform(-20, 20, (40, 3)),
        )
        _png(drive / "image_02" / "data" / f"{i:010d}.png")
        (drive / "oxts" / "data" / f"{i:010d}.txt").write_text(row)
    calib = load_calib(date)
    assert calib.image_size == (1242, 375)
    sensor = read_scene(build_kitti_raw(drive, tmp_path / "out"))
    assert sensor.path.name == "2011_09_26_drive_0001_sync.lidar.zip"
    assert [f["timestamp"] for f in sensor.frames] == pytest.approx([0, 0.11, 0.2])
    world = read_scene(
        build_kitti_raw(drive, tmp_path / "out" / "w.lidar.zip", world=True)
    )
    for i in range(3):
        m = np.array(
            world.frames[i]["images"]["front"]["world_to_image"]
        ) @ world.ego_pose(i)
        assert np.allclose(
            m, np.diag([0.5, 0.5, 1]) @ calib.velo_to_image, rtol=1e-4, atol=1e-3
        )
        assert (
            np.abs(
                g.transform_points(g.invert(world.ego_pose(i)), world.points(i).xyz)
                - sensor.points(i).xyz
            ).max()
            < 0.011
        )

    (drive / "tracklet_labels.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<boost_serialization signature="serialization::archive" version="9">
<tracklets class_id="0" tracking_level="0" version="0"><count>2</count><item_version>1</item_version>
<item class_id="1" tracking_level="0" version="1"><objectType>Car</objectType><h>1.5</h><w>1.6</w><l>4.0</l>
<first_frame>1</first_frame><poses class_id="2" tracking_level="0" version="0"><count>2</count><item_version>2</item_version>
<item><tx>10.0</tx><ty>2.0</ty><tz>-1.7</tz><rx>0</rx><ry>0</ry><rz>0.3</rz><state>1</state></item>
<item><tx>11.0</tx><ty>2.1</ty><tz>-1.7</tz><rx>0</rx><ry>0</ry><rz>0.31</rz><state>1</state></item>
</poses><finished>1</finished></item>
<item><objectType>Cyclist</objectType><h>1.7</h><w>0.6</w><l>1.8</l><first_frame>0</first_frame>
<poses><count>1</count><item_version>2</item_version>
<item><tx>-5.0</tx><ty>1.0</ty><tz>-1.6</tz><rx>0</rx><ry>0</ry><rz>-1.0</rz><state>1</state></item>
</poses><finished>1</finished></item>
</tracklets></boost_serialization>"""
    )
    af = parse_kitti_tracklets(drive / "tracklet_labels.xml")[0]
    assert (
        af.filename == "2011_09_26_drive_0001_sync.lidar.zip"
        and af.slots[0].frame_count == 3
    )
    car, cyclist = af.annotations
    assert car.segments == [[1, 3]] and cyclist.segments == [[0, 1]]
    assert car.frames[2].data["position"] == pytest.approx(
        {"x": 11.0, "y": 2.1, "z": -0.95}
    )
    assert car.frames[2].data["dimensions"] == {"x": 4.0, "y": 1.6, "z": 1.5}
    assert car.frames[1].data["rotation"]["z"] == pytest.approx(0.3)
    assert (
        frame_objects(af)[1][0].instance_id == 1
        and cyclist.frames[0].get_sub("instance_id").data == 2
    )
    world_af = parse_kitti_tracklets(drive / "tracklet_labels.xml", world=True)[0]
    box = g.to_ego_frame(world_af.annotations[0].frames[2].data, world.ego_pose(2))
    assert box["position"] == pytest.approx(car.frames[2].data["position"], abs=1e-4)


def test_object_builder(object_root, tmp_path):
    (path,) = build_kitti_object(object_root.parent, tmp_path, frame_ids=[1])
    assert path.name == "kitti_object_training_000001.lidar.zip"
    scene = read_scene(path)
    raw = np.fromfile(object_root / "velodyne" / "000001.bin", "<f4").reshape(-1, 4)
    assert len(scene) == 1 and np.abs(scene.points(0).xyz - raw[:, :3]).max() <= 0.0051
    assert "front" in scene.frames[0]["images"]


def test_registered_formats(object_root, tracking_root, tmp_path):
    parse_path = get_importer("kitti_3d")
    assert parse_path(object_root / "label_2" / "000001.txt")[0].filename.startswith(
        "kitti_object"
    )
    assert (
        parse_path(tracking_root / "label_02" / "0000.txt")[0].slots[0].frame_count == 3
    )
    assert parse_path(tracking_root / "calib" / "0000.txt") is None
    assert parse_path(tracking_root / "label_02") is None
    af = parse_path(object_root / "label_2" / "000001.txt")[0]
    get_exporter("kitti_3d")([af], tmp_path / "out")
    lines = _rows(
        (tmp_path / "out" / "kitti_object_training_000001" / "000000.txt").read_text()
    )
    assert [r[7] for r in lines] == ["Car", "Pedestrian"]


def test_export_calibration_replaces_the_calib_file(
    tracking_root, tmp_path, check_calibration, with_package_calibration
):
    from darwin.lidar.kitti import read_oxts, world_poses

    calib_file = tracking_root / "calib" / "0000.txt"
    calib = load_calib(calib_file)
    path = build_kitti_tracking(
        tracking_root.parent, 0, tmp_path / "pkg", world=True, image_scale=1
    )
    manifest = read_scene(path).manifest
    check_calibration(manifest)
    world = world_poses(read_oxts(tracking_root / "oxts" / "0000.txt"), calib)
    assert manifest["origin"] == pytest.approx(world[0, :3, 3].tolist(), abs=1e-6)
    labels = tracking_root / "label_02" / "0000.txt"
    plain = parse_kitti_tracking(labels, world=True)[0]
    calibrated = parse_darwin_json(
        write_darwin_json(with_package_calibration(plain, manifest), tmp_path / "json")
    )
    big = (10_000, 10_000)

    def rows(af, name, **kw):
        export_kitti([af], tmp_path / name, tracking=True, image_size=big, **kw)
        return _rows((tmp_path / name / "kitti_tracking_training_0000.txt").read_text())

    reference = rows(plain, "ref", calib=calib_file)
    assert rows(calibrated, "explicit", calib=calib_file) == reference  # calib wins
    exported = rows(calibrated, "export")
    export_kitti([plain], tmp_path / "none", tracking=True)
    assert not (tmp_path / "none").exists()  # no calibration anywhere: skipped
    baseline = np.linalg.solve(calib.P2[:, :3], calib.P2[:, 3])
    assert len(exported) == len(reference) == 5
    for e, r in zip(exported, reference):
        assert e[:3] == r[:3]
        nums = lambda row, a, b: np.array(row[a:b], float)  # noqa: E731
        assert np.allclose(nums(e, 6, 13), nums(r, 6, 13), atol=1e-3)  # 2D box, h w l
        # camera frame of image_02: KITTI's rectified cam0 frame + the P2 baseline
        assert np.allclose(nums(e, 13, 16), nums(r, 13, 16) + baseline, atol=1e-4)
        assert float(e[16]) == pytest.approx(float(r[16]), abs=1e-5)

    export_kitti([calibrated], tmp_path / "front", camera="front", image_size=big)
    front = _rows(
        (tmp_path / "front" / "kitti_tracking_training_0000" / "000001.txt").read_text()
    )
    assert [r[:1] + r[4:8] for r in front] == [
        [r[2]] + r[6:10] for r in exported if r[0] == "1"
    ]
    export_kitti([calibrated], tmp_path / "pcdet")  # no calib, no camera: lidar frame
    lidar = tmp_path / "pcdet" / "kitti_tracking_training_0000" / "000001.txt"
    assert [len(r) for r in _rows(lidar.read_text())] == [8, 8]
