import struct
import zipfile

import numpy as np
import pytest

from darwin.lidar import geometry as g
from darwin.lidar.pointcloud import (
    _lzf_decompress,
    pcd_bytes,
    read_pcd,
    read_points,
)
from darwin.lidar.scene import CameraImage, Frame, read_scene, write_scene

RNG = np.random.default_rng(0)


def test_quaternion_and_euler_round_trip():
    for _ in range(20):
        roll, pitch, yaw = RNG.uniform(-1.4, 1.4, 3)
        r = g.euler_to_rot(roll, pitch, yaw)
        assert np.allclose(g.rot_to_euler(r), (roll, pitch, yaw))
        q = g.rot_to_quat(r)
        assert np.allclose(g.quat_to_rot(*q), r)
    r90 = g.quat_to_rot(np.cos(np.pi / 4), 0, 0, np.sin(np.pi / 4))
    assert np.allclose(r90 @ [1, 0, 0], [0, 1, 0])
    assert np.allclose(g.rot_to_quat(np.diag([1.0, -1, -1])), (0, 1, 0, 0))


def test_to_ego_frame_known_transform():
    # ego at (10, 5, 0) heading +90 deg: a box 2 m ahead of the ego sits at (10, 7) in the scene
    ego = g.make_pose(g.euler_to_rot(0, 0, np.pi / 2), (10, 5, 0))
    scene_box = {
        "position": {"x": 10, "y": 7, "z": 1},
        "dimensions": {"x": 4, "y": 2, "z": 1.5},
        "rotation": {"x": 0, "y": 0, "z": np.pi / 2 + 0.1},
    }
    ego_box = g.to_ego_frame(scene_box, ego)
    assert np.allclose([ego_box["position"][k] for k in "xyz"], [2, 0, 1])
    assert np.isclose(ego_box["rotation"]["z"], 0.1)
    back = g.to_scene_frame(ego_box, ego)
    assert np.allclose([back["position"][k] for k in "xyz"], [10, 7, 1])
    assert g.to_ego_frame(
        {"x": 10, "y": 7, "z": 0}, ego, "keypoint_3d"
    ) == pytest.approx({"x": 2, "y": 0, "z": 0})
    path = g.to_ego_frame({"path": [{"x": 10, "y": 5, "z": 0}]}, ego, "polyline_3d")
    assert path["path"][0] == pytest.approx({"x": 0, "y": 0, "z": 0})
    mask = {"point_count": 3, "ranges": [0, 1]}
    assert g.to_ego_frame(mask, ego, "point_mask_3d") is mask


def test_full_rotation_round_trip_and_yaw_only():
    pose = g.make_pose(g.euler_to_rot(0.05, -0.03, 1.0), (3, 4, 5))
    box = {
        "position": {"x": 1, "y": 2, "z": 3},
        "dimensions": {"x": 4, "y": 2, "z": 1},
        "rotation": {"x": 0.1, "y": 0.2, "z": -2.0},
    }
    back = g.to_scene_frame(g.to_ego_frame(box, pose), pose)
    for k in ("position", "rotation"):
        assert [back[k][a] for a in "xyz"] == pytest.approx([box[k][a] for a in "xyz"])
    assert g.yaw_only(box)["rotation"]["x"] == 0
    corners = g.box_corners({**box, "rotation": {"x": 0, "y": 0, "z": 0}})
    assert np.allclose(corners.mean(0), [1, 2, 3])
    assert np.allclose(corners[0], [3, 3, 2.5])


def test_ego_pose_of():
    meta = {
        "coordinate_frame": "world",
        "frames": [{"timestamp": 0, "ego_pose": np.eye(4).tolist()}],
    }
    assert np.allclose(g.ego_pose_of(meta, 0), np.eye(4))
    assert g.ego_pose_of({"coordinate_frame": "sensor", "frames": [{}]}, 0) is None
    assert g.ego_pose_of(meta, 5) is None


def _pcd_header(fields, sizes, types, n, data):
    return (
        f"VERSION 0.7\nFIELDS {fields}\nSIZE {sizes}\nTYPE {types}\nCOUNT {' '.join(['1'] * len(fields.split()))}\n"
        f"WIDTH {n}\nHEIGHT 1\nVIEWPOINT 0 0 0 1 0 0 0\nPOINTS {n}\nDATA {data}\n"
    ).encode()


def test_pcd_ascii_binary_and_compressed(tmp_path):
    xyz = RNG.normal(size=(5, 3)).astype(np.float32)
    inten = np.arange(5, dtype=np.float32)
    ascii_body = "\n".join(
        " ".join(f"{v:.9g}" for v in (*p, i)) for p, i in zip(xyz, inten)
    )
    ascii = (
        _pcd_header("x y z intensity", "4 4 4 4", "F F F F", 5, "ascii")
        + ascii_body.encode()
    )
    binary = read_pcd(pcd_bytes(xyz, None))
    # binary_compressed: field-major columns, LZF stream made of literal runs
    cols = b"".join(np.ascontiguousarray(c).tobytes() for c in (*xyz.T, inten))
    lzf = b"".join(
        bytes([len(cols[k : k + 32]) - 1]) + cols[k : k + 32]
        for k in range(0, len(cols), 32)
    )
    compressed = (
        _pcd_header("x y z intensity", "4 4 4 4", "F F F F", 5, "binary_compressed")
        + struct.pack("<II", len(lzf), len(cols))
        + lzf
    )
    for cloud in (read_pcd(ascii), read_pcd(compressed)):
        assert np.allclose(cloud.xyz, xyz) and np.allclose(cloud.intensity, inten)
    assert np.allclose(binary.xyz, xyz) and binary.intensity is None
    (tmp_path / "a.pcd").write_bytes(compressed)
    assert np.allclose(read_points(tmp_path / "a.pcd").xyz, xyz)


def test_lzf_back_reference():
    # literal "A", then a back reference of length 3 at distance 1 (overlapping copy)
    assert _lzf_decompress(bytes([0, 65, 0b00100000, 0]), 4) == b"AAAA"
    assert _lzf_decompress(bytes([1, 65, 66, 0b00100000, 1]), 5) == b"ABABA"


def test_other_readers(tmp_path):
    xyz = RNG.normal(size=(4, 3)).astype(np.float32)
    kitti = np.c_[xyz, [0.1, 0.2, 0.3, 0.4]].astype("<f4")
    kitti.tofile(tmp_path / "a.bin")
    np.c_[kitti, np.zeros(4)].astype("<f4").tofile(tmp_path / "b.pcd.bin")
    np.save(tmp_path / "c.npy", kitti)
    ply_rec = np.zeros(
        4, [("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("intensity", "u1")]
    )
    ply_rec["x"], ply_rec["y"], ply_rec["z"] = xyz.T
    ply_rec["intensity"] = [1, 2, 3, 4]
    header = (
        "ply\nformat binary_little_endian 1.0\nelement vertex 4\nproperty float x\n"
        "property float y\nproperty float z\nproperty uchar intensity\nelement face 0\n"
        "property list uchar int vertex_indices\nend_header\n"
    )
    (tmp_path / "d.ply").write_bytes(header.encode() + ply_rec.tobytes())
    ascii_ply = "ply\nformat ascii 1.0\nelement vertex 4\nproperty float x\nproperty float y\nproperty float z\nend_header\n"
    ascii_ply += "\n".join(" ".join(f"{v:.9g}" for v in p) for p in xyz)
    (tmp_path / "e.ply").write_text(ascii_ply)
    for name in ("a.bin", "b.pcd.bin", "c.npy", "d.ply", "e.ply"):
        assert np.allclose(read_points(tmp_path / name).xyz, xyz), name
    assert np.allclose(read_points(tmp_path / "b.pcd.bin").intensity, kitti[:, 3])
    assert np.allclose(read_points(tmp_path / "d.ply").intensity, [1, 2, 3, 4])


def test_las_reader(tmp_path):
    laspy = pytest.importorskip("laspy")
    las = laspy.create(point_format=0, file_version="1.2")
    las.header.scales = [0.001] * 3
    las.x, las.y, las.z = [1.0, 2.5], [3.0, 4.25], [0.5, -1.0]
    las.intensity = [10, 20]
    las.write(tmp_path / "a.las")
    cloud = read_points(tmp_path / "a.las")
    assert np.allclose(cloud.xyz, [[1, 3, 0.5], [2.5, 4.25, -1]])
    assert np.allclose(cloud.intensity, [10, 20])


def test_write_scene_world_quantized_with_camera(tmp_path):
    from PIL import Image

    frames, poses = [], []
    for t in range(3):
        pose = g.make_pose(g.euler_to_rot(0, 0, 0.1 * t), (5.0 * t, 0, 0))
        pts = RNG.uniform(-50, 50, (200, 3)) + pose[:3, 3]
        img = Image.fromarray(RNG.integers(0, 255, (40, 60, 3), dtype=np.uint8))
        k = np.array([[50.0, 0, 30, 0], [0, 50, 20, 0], [0, 0, 1, 0]])
        frames.append(
            Frame(
                pts,
                RNG.uniform(0, 1, 200),
                100 + t / 10,
                pose,
                {"front": CameraImage(img, k)},
            )
        )
        poses.append(pose)
    out = write_scene(tmp_path / "s.lidar.zip", iter(frames), fps=10, image_scale=0.5)
    with zipfile.ZipFile(out) as z:
        infos = z.infolist()
        assert (
            infos[0].filename == "scene.json"
            and infos[0].compress_type == zipfile.ZIP_STORED
        )
        assert all(not (i.flag_bits & 0x08) for i in infos)  # no data descriptors
        assert z.getinfo("lidar/000001.pcd").compress_type == zipfile.ZIP_DEFLATED
        assert z.getinfo("cameras/front/000002.jpg").compress_type == zipfile.ZIP_STORED
    scene = read_scene(out)
    m = scene.manifest
    assert (
        m["version"] == 2
        and m["coordinate_frame"] == "world"
        and m["points"] == {"scale": 0.01}
    )
    assert m["cameras"] == [{"name": "front", "width": 30, "height": 20}]
    assert [f["timestamp"] for f in m["frames"]] == pytest.approx([0, 0.1, 0.2])
    assert np.allclose(
        m["frames"][0]["images"]["front"]["world_to_image"][0], [25, 0, 15, 0]
    )
    for t in range(3):
        assert np.abs(scene.points(t).xyz - frames[t].points).max() <= 0.005 + 1e-9
        assert np.allclose(scene.ego_pose(t), poses[t], atol=1e-6)
    assert b"TYPE I I I U" in scene.read("lidar/000000.pcd")[:300]


def test_write_scene_sensor_float_fallback(tmp_path):
    far = np.array([[0, 0, 0], [1000.0, 0, 0], [np.nan, 0, 0]])
    out = write_scene(tmp_path / "f.lidar.zip", [Frame(far)], coordinate_frame="sensor")
    scene = read_scene(out)
    assert "points" not in scene.manifest and "ego_pose" not in scene.frames[0]
    assert np.allclose(scene.points(0).xyz, far, equal_nan=True)
    with pytest.raises(ValueError):
        write_scene(tmp_path / "w.lidar.zip", [Frame(far)], coordinate_frame="world")
