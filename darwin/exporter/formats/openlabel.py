from pathlib import Path
from typing import Iterable

import darwin.datatypes as dt
from darwin.lidar.openlabel import export_openlabel


def export(annotation_files: Iterable[dt.AnnotationFile], output_dir: Path) -> None:
    """Exports the 3D annotations of ``pointcloud`` items as ASAM OpenLABEL 1.0 JSON."""
    export_openlabel(annotation_files, output_dir)
