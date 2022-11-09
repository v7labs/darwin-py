import tempfile
from pathlib import Path
from zipfile import ZipFile

import nibabel as nib
import numpy as np
from darwin.exporter.exporter import darwin_to_dt_gen
from darwin.exporter.formats import nifti


def test_video_annotation_nifti_export():
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile("tests/data.zip") as zfile:
            zfile.extractall(tmpdir)
            annotations_dir = Path(tmpdir) / "v7/nifti/releases/latest/annotations"
            video_annotation_filepaths = [
                f
                for f in annotations_dir.iterdir()
                if f.suffix == ".json" and f != annotations_dir / "image_annotation.json"
            ]
            video_annotations = list(darwin_to_dt_gen(video_annotation_filepaths))
            nifti.export(video_annotations, output_dir=tmpdir)
            export_im = nib.load(Path(tmpdir) / "vol0002_brain.nii.gz").get_fdata()
            expected_im = nib.load(annotations_dir / "vol0002_brain.nii.gz").get_fdata()
            assert np.allclose(export_im, expected_im)


def test_image_annotation_nifti_export():
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile("tests/data.zip") as zfile:
            zfile.extractall(tmpdir)
            annotations_dir = Path(tmpdir) / "v7/nifti/releases/latest/annotations"
            image_annotation_filepath = annotations_dir / "image_annotation.json"
            image_annotations = list(darwin_to_dt_gen([image_annotation_filepath]))
            nifti.export(image_annotations, output_dir=tmpdir)
            export_im = nib.load(Path(tmpdir) / "vol0_brain.nii.gz").get_fdata()
            expected_im = nib.load(annotations_dir / "vol0_brain.nii.gz").get_fdata()
            assert np.allclose(export_im, expected_im)
