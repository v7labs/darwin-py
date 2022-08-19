import os
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

import darwin.datatypes as dt
import nibabel as nib
import numpy as np
import pytest
from darwin.exporter.formats import nifti
from darwin.utils import parse_darwin_json
from tests.fixtures import *
from yaml import parse

# @pytest.fixture
# def video_annotation() -> dt.AnnotationFile:
#     return parse_darwin_json(Path("v7/nifti/annotations/vol0.json"))


def test_nifti(team_slug: str, team_extracted_dataset_path: Path):
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile("tests/data.zip") as zfile:
            zfile.extractall(tmpdir)
        video_annotation = parse_darwin_json(Path(tmpdir) / "v7/nifti/releases/latest/annotations/0.json")
        nifti.export([video_annotation], output_dir=tmpdir)
        image_id = os.path.splitext(video_annotation.filename)[0]
        export_im = nib.load(Path(tmpdir) / f"{image_id}.nii.gz").get_fdata()
        expected_im = nib.load("tests/output.nii.gz").get_fdata()
        assert np.allclose(export_im, expected_im)
