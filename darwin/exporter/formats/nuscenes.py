from pathlib import Path
from typing import Iterable

import darwin.datatypes as dt
from darwin.lidar.nuscenes import export_nuscenes


def export(annotation_files: Iterable[dt.AnnotationFile], output_dir: Path) -> None:
    """``cuboid_3d`` -> nuScenes ``sample_annotation``-like JSON per item, in the scene frame."""
    export_nuscenes(annotation_files, output_dir)
