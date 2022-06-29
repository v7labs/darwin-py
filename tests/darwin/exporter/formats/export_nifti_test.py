import os
import tempfile
import unittest
from pathlib import Path

import darwin.datatypes as dt
import nibabel as nib
import numpy as np
import pytest
from darwin.exporter.formats import nifti
from darwin.utils import parse_darwin_json
from yaml import parse


@pytest.fixture
def video_annotation() -> dt.AnnotationFile:
    return parse_darwin_json(Path("tests/v7/nifti/annotations/vol0.json"))


def test_nifti(video_annotation: dt.AnnotationFile):
    with tempfile.TemporaryDirectory() as tmpdir:
        nifti.export([video_annotation], output_dir=tmpdir)
        image_id = os.path.splitext(video_annotation.filename)[0]
        export_im = nib.load(Path(tmpdir) / f"{image_id}.nii.gz").get_fdata()
        expected_im = nib.load("tests/v7/nifti/annotations/output.nii").get_fdata()
        assert np.allclose(export_im, expected_im)
