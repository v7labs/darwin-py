from pathlib import Path
from typing import Iterable

import darwin.datatypes as dt
from darwin.exporter.formats.nifti import export_single_nifti_file


def export(annotation_files: Iterable[dt.AnnotationFile], output_dir: Path) -> None:
    """
    Exports the given ``AnnotationFile``\\s into nifti format inside of the given
    ``output_dir``. Deletes everything within ``output_dir/masks`` before writting to it.

    Parameters
    ----------
    annotation_files : Iterable[dt.AnnotationFile]
        The ``AnnotationFile``\\s to be exported.
    output_dir : Path
        The folder where the new instance mask files will be.
    """
    video_annotations = list(annotation_files)
    for video_annotation in video_annotations:
        export_single_nifti_file(video_annotation, output_dir, multilabel=True)
