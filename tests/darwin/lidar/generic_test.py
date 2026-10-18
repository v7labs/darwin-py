import numpy as np
import pytest

from darwin.lidar import geometry as g
from darwin.lidar.generic import build_pointcloud, convert_cloud, load_poses
from darwin.lidar.pointcloud import read_pcd
from darwin.lidar.scene import read_scene


def _clouds(tmp_path, n=3):
    d = tmp_path / "seq"
    d.mkdir()
    rng = np.random.default_rng(1)
    clouds = [rng.uniform(-20, 20, (50, 4)).astype("<f4") for _ in range(n)]
    for i, c in enumerate(clouds):
        c[:, 3] = np.abs(c[:, 3]) / 20
        c.tofile(d / f"{i}.bin")
    (d / "notes.txt").write_text("ignored")
    return d, clouds


def test_convert_single_cloud(tmp_path):
    d, clouds = _clouds(tmp_path, 1)
    out = convert_cloud(d / "0.bin", tmp_path / "out")
    assert out.name == "0.pcd"
    cloud = read_pcd(out)
    assert np.allclose(cloud.xyz, clouds[0][:, :3], atol=1e-6)


def test_sequence_sensor_frame(tmp_path):
    d, clouds = _clouds(tmp_path)
    scene = read_scene(build_pointcloud(d, tmp_path))
    assert scene.path.name == "seq.lidar.zip"
    assert scene.manifest["coordinate_frame"] == "sensor" and len(scene) == 3
    for i, c in enumerate(clouds):
        assert np.abs(scene.points(i).xyz - c[:, :3]).max() <= 0.0051


def test_sequence_with_kitti_style_poses(tmp_path):
    d, clouds = _clouds(tmp_path)
    world = [
        g.make_pose(g.euler_to_rot(0, 0, 0.3 * i), (100 + 2 * i, 50, 1))
        for i in range(3)
    ]
    poses_txt = tmp_path / "poses.txt"
    poses_txt.write_text("\n".join(" ".join(map(str, p[:3].ravel())) for p in world))
    assert np.allclose(load_poses(poses_txt), world)
    scene = read_scene(build_pointcloud(d, tmp_path / "x.lidar.zip", poses=poses_txt))
    assert scene.manifest["coordinate_frame"] == "world"
    assert scene.manifest["origin"] == pytest.approx([100, 50, 1])
    for i, c in enumerate(clouds):
        ego = scene.ego_pose(i)
        assert np.allclose(ego[:3, 3], world[i][:3, 3] - world[0][:3, 3], atol=1e-6)
        expected = g.transform_points(ego, c[:, :3])
        assert np.abs(scene.points(i).xyz - expected).max() <= 0.0051
