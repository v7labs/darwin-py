from pathlib import Path
from typing import Iterable

import darwin.datatypes as dt
from darwin.exporter.formats.mask import export as export_mask


def export(annotation_files: Iterable[dt.AnnotationFile], output_dir: Path) -> None:
    """
    Exports the given ``AnnotationFile``\\s into semantic masks inside of the given ``output_dir``.

    Parameters
    ----------
    annotation_files : Iterable[dt.AnnotationFile]
        The ``AnnotationFile``\\s to be exported.
    output_dir : Path
        The folder where the new semantic mask files will be.
    """
    return export_mask(annotation_files=annotation_files, output_dir=output_dir, mode="rgb")
