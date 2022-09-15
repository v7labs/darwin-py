import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import deprecation
import nibabel as nib
import numpy as np
from upolygon import find_contours, rle_decode

import darwin.datatypes as dt
from darwin.path_utils import deconstruct_full_path
from darwin.version import __version__


def parse_path(path: Path) -> Optional[List[dt.AnnotationFile]]:
    """
    Parses the given ``nifti`` file and returns a ``List[dt.AnnotationFile]`` with the parsed
    information.

    Parameters
    ----------
    path : Path
        The ``Path`` to the ``nifti`` file.

    Returns
    -------
    Optional[List[dt.AnnotationFile]]
        Returns ``None`` if the given file is not in ``json`` format, or ``List[dt.AnnotationFile]``
        otherwise.
    """
    if ".".join(path.suffixes) not in [".nii", ".nii.gz"]:
        return None
    nifti_image = nib.load(path)
    return list(parse_nifti(nifti_image, path))


def parse_nifti(img: nib.Nifti1Image, path: Path) -> Iterator[dt.AnnotationFile]:
    shape = img.shape
    annotation_files = []
    for i in range(shape[0]):
        slice_mask = img[i, :, :].astype(np.uint8)
        _labels, external_paths, _internal_paths = find_contours(slice_mask)
        annotations = []
        for external_path in external_paths:
            polygon = dt.make_polygon(
                "test_class",
                point_path=[
                    {"x": x, "y": y}
                    for x, y in zip(external_path[0::2], external_path[1::2])
                ],
            )
            annotations.append(polygon)
        annotation_file = dt.AnnotationFile(
            path, "test_filename", ["test_class"], annotations, remote_path="test_path"
        )
        annotation_files.append(annotation_file)
    return annotation_files
