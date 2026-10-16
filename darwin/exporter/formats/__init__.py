from typing import List

# When updating this file, please also update the docs:
# https://docs.v7labs.com/docs/convert-1
supported_formats: List[str] = [
    "coco",
    "cvat",
    "dataloop",
    "instance_mask",
    "pascalvoc",
    "semantic_mask",
    "semantic_mask_grey",
    "semantic_mask_index",
    "yolo",
    "yolo_segmented",
    "nifti",
    # LiDAR (darwin.lidar)
    "argoverse2",
    "kitti_3d",
    "lidar_ego",
    "nuscenes",
    "openlabel",
    "semantic_kitti",
]
