from pathlib import Path
from typing import Iterable

import darwin.datatypes as dt
from darwin.lidar.ego import export_ego


def export(annotation_files: Iterable[dt.AnnotationFile], output_dir: Path) -> None:
    """Exports the 3D annotations of ``pointcloud`` items in each sweep's ego frame."""
    export_ego(annotation_files, output_dir)
