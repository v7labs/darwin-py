from pathlib import Path
from typing import Iterator

import darwin.datatypes as dt
from darwin.lidar.semantic_kitti import export_semantic_kitti


def export(annotation_files: Iterator[dt.AnnotationFile], output_dir: Path) -> None:
    """Darwin ``point_mask_3d`` annotations -> SemanticKITTI ``.label`` files."""
    export_semantic_kitti(annotation_files, output_dir)
