from pathlib import Path
from typing import Iterable

import darwin.datatypes as dt
from darwin.lidar.kitti import export_kitti


def export(annotation_files: Iterable[dt.AnnotationFile], output_dir: Path) -> None:
    """
    LiDAR ``cuboid_3d`` annotations -> per-frame ``x y z dx dy dz heading class`` label files
    in the lidar (ego) frame. Use ``darwin.lidar.kitti.export_kitti`` with ``calib`` for
    KITTI camera-frame ``label_2`` / ``label_02`` files.
    """
    export_kitti(annotation_files, output_dir)
