import tempfile
from pathlib import Path
from zipfile import ZipFile

import nibabel as nib
import numpy as np
from darwin.exporter.exporter import darwin_to_dt_gen
from darwin.exporter.formats import nifti


def test_video_annotation_nifti_export_v2():
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile("tests/data.zip") as zfile:
            zfile.extractall(tmpdir)
            annotations_dir = Path(tmpdir) / "v7/nifti/releases/latest/annotations"
            video_annotation_filepaths = [annotations_dir / "hippocampus_001.nii.json"]
            video_annotations = list(darwin_to_dt_gen(video_annotation_filepaths, False))
            nifti.export(video_annotations, output_dir=tmpdir)
            export_im = nib.load(Path(tmpdir) / "hippocampus_001_hippocampus.nii.gz").get_fdata()
            expected_im = nib.load(annotations_dir / "hippocampus_001_hippocampus.nii.gz").get_fdata()
            assert np.allclose(export_im, expected_im)
