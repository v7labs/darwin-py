from pathlib import Path
from typing import Iterable

import darwin.datatypes as dt
from darwin.exporter.formats.mask import export as export_mask


def export(annotation_files: Iterable[dt.AnnotationFile], output_dir: Path) -> None:
    return export_mask(annotation_files=annotation_files, output_dir=output_dir, mode="index")
