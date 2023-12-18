import tempfile
from pathlib import Path
from zipfile import ZipFile

import nibabel as nib
import numpy as np

from darwin.exporter.exporter import darwin_to_dt_gen
from darwin.exporter.formats import nifti
from tests.fixtures import *


def test_video_annotation_nifti_export_single_slot(team_slug: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile("tests/data.zip") as zfile:
            zfile.extractall(tmpdir)
            annotations_dir = (
                Path(tmpdir) / team_slug / "nifti/releases/latest/annotations"
            )
            video_annotation_filepaths = [annotations_dir / "hippocampus_001.nii.json"]
            video_annotations = list(
                darwin_to_dt_gen(video_annotation_filepaths, False)
            )
            nifti.export(video_annotations, output_dir=tmpdir)
            export_im = nib.load(
                annotations_dir / "hippocampus_001_hippocampus.nii.gz"
            ).get_fdata()
            expected_im = nib.load(
                annotations_dir / "hippocampus_001_hippocampus.nii.gz"
            ).get_fdata()
            assert np.allclose(export_im, expected_im)


def test_video_annotation_nifti_export_multi_slot(team_slug: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile("tests/data.zip") as zfile:
            zfile.extractall(tmpdir)
            annotations_dir = (
                Path(tmpdir) / team_slug / "nifti/releases/latest/annotations"
            )
            video_annotation_filepaths = [
                annotations_dir / "hippocampus_multislot.nii.json"
            ]
            video_annotations = list(
                darwin_to_dt_gen(video_annotation_filepaths, False)
            )
            nifti.export(video_annotations, output_dir=tmpdir)
            names = ["1", "2", "3", "4", "5"]
            for slotname in names:
                export_im = nib.load(
                    annotations_dir
                    / f"hippocampus_multislot_{slotname}_test_hippo.nii.gz"
                ).get_fdata()
                expected_im = nib.load(
                    annotations_dir
                    / f"hippocampus_multislot_{slotname}_test_hippo.nii.gz"
                ).get_fdata()
                assert np.allclose(export_im, expected_im)


def test_video_annotation_nifti_export_mpr(team_slug: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile("tests/data.zip") as zfile:
            zfile.extractall(tmpdir)
            annotations_dir = (
                Path(tmpdir) / team_slug / "nifti/releases/latest/annotations"
            )
            video_annotation_filepaths = [
                annotations_dir / "hippocampus_multislot_001_mpr.json"
            ]
            video_annotations = list(
                darwin_to_dt_gen(video_annotation_filepaths, False)
            )
            nifti.export(video_annotations, output_dir=tmpdir)
            export_im = nib.load(
                annotations_dir / "hippocampus_001_mpr_1_test_hippo.nii.gz"
            ).get_fdata()
            expected_im = nib.load(
                annotations_dir / "hippocampus_001_mpr_1_test_hippo.nii.gz"
            ).get_fdata()
            assert np.allclose(export_im, expected_im)
