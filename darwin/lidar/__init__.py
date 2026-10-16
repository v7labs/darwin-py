"""
LiDAR / multi-camera support: scene packages for upload (``.lidar.zip`` / ``.pcd``), dataset
label importers, exporters and scene <-> ego frame helpers. See ``docs/lidar.md``.

Dataset modules: ``darwin.lidar.kitti``, ``semantic_kitti``, ``nuscenes``, ``av2``,
``pandaset``, ``openlabel``, ``ego``. Command line: ``python -m darwin.lidar``.
"""

from darwin.lidar.darwin_json import (  # noqa: F401
    frame_objects,
    make_lidar_file,
    make_track,
    mask_to_ranges,
    ranges_to_indices,
    to_darwin_json,
    write_darwin_json,
)
from darwin.lidar.generic import build_pointcloud, convert_cloud  # noqa: F401
from darwin.lidar.geometry import (  # noqa: F401
    ego_pose_of,
    to_ego_frame,
    to_scene_frame,
    yaw_only,
)
from darwin.lidar.pointcloud import read_points, write_pcd  # noqa: F401
from darwin.lidar.scene import CameraImage, Frame, read_scene, write_scene  # noqa: F401
