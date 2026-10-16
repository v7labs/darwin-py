from pathlib import Path
from typing import Iterable

import darwin.datatypes as dt


def export(annotation_files: Iterable[dt.AnnotationFile], output_dir: Path) -> None:
    """LiDAR cuboids -> Argoverse 2 ``<item>/annotations.feather`` in the ego frame of each sweep."""
    from darwin.lidar.av2 import export_av2

    export_av2(annotation_files, output_dir)
