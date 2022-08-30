import os
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

import darwin.datatypes as dt
import nibabel as nib
import numpy as np
import pytest
from darwin.exporter.exporter import darwin_to_dt_gen
from darwin.exporter.formats import nifti
from darwin.utils import parse_darwin_json
from tests.fixtures import *
from yaml import parse


def test_nifti(team_slug: str, team_extracted_dataset_path: Path):
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile("tests/v7 2 2.zip") as zfile:
            zfile.extractall(tmpdir)
        filepath = Path(tmpdir) / "v7 2 2/nifti/annotations"
        filepaths = [f for f in filepath.iterdir() if f.suffix == ".json"]
        video_annotations = darwin_to_dt_gen(filepaths)
        nifti.export(video_annotations, output_dir=tmpdir)
        export_im = nib.load(Path(tmpdir) / "vol0_3_brain.nii.gz").get_fdata()
        expected_im = nib.load("tests/output.nii.gz").get_fdata()
        assert np.allclose(export_im, expected_im)
