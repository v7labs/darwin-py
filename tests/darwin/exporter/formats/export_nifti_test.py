import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from zipfile import ZipFile

import nibabel as nib
import numpy as np

from darwin.exporter.exporter import darwin_to_dt_gen
from darwin.exporter.formats import nifti
from darwin.exporter.formats.nifti import (
    populate_output_volumes_from_raster_layer,
    Volume,
)
import darwin.datatypes as dt
from tests.fixtures import *


def test_video_annotation_nifti_export_single_slot(team_slug_darwin_json_v2: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile("tests/data.zip") as zfile:
            zfile.extractall(tmpdir)
            annotations_dir = (
                Path(tmpdir)
                / team_slug_darwin_json_v2
                / "nifti/releases/latest/annotations"
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


def test_video_annotation_nifti_export_multi_slot(team_slug_darwin_json_v2: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile("tests/data.zip") as zfile:
            zfile.extractall(tmpdir)
            annotations_dir = (
                Path(tmpdir)
                / team_slug_darwin_json_v2
                / "nifti/releases/latest/annotations"
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


def test_video_annotation_nifti_export_mpr(team_slug_darwin_json_v2: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile("tests/data.zip") as zfile:
            zfile.extractall(tmpdir)
            annotations_dir = (
                Path(tmpdir)
                / team_slug_darwin_json_v2
                / "nifti/releases/latest/annotations"
            )
            video_annotation_filepaths = [
                annotations_dir / "hippocampus_multislot_001_mpr.json"
            ]
            video_annotations = list(
                darwin_to_dt_gen(video_annotation_filepaths, False)
            )
            nifti.export(video_annotations, output_dir=Path(tmpdir))
            export_im = nib.load(
                annotations_dir / "hippocampus_001_mpr_1_test_hippo.nii.gz"
            ).get_fdata()
            expected_im = nib.load(
                annotations_dir / "hippocampus_001_mpr_1_test_hippo.nii.gz"
            ).get_fdata()
            assert np.allclose(export_im, expected_im)


def test_export_calls_populate_output_volumes_from_polygons(
    team_slug_darwin_json_v2: str,
):
    with patch(
        "darwin.exporter.formats.nifti.populate_output_volumes_from_polygons"
    ) as mock:
        with tempfile.TemporaryDirectory() as tmpdir:
            with ZipFile("tests/data.zip") as zfile:
                zfile.extractall(tmpdir)
            annotations_dir = (
                Path(tmpdir)
                / team_slug_darwin_json_v2
                / "nifti/releases/latest/annotations"
            )
            video_annotation_filepaths = [annotations_dir / "polygon_only.json"]
            video_annotations = list(
                darwin_to_dt_gen(video_annotation_filepaths, False)
            )
            nifti.export(video_annotations, output_dir=Path(tmpdir))
            mock.assert_called()


def test_export_calls_populate_output_volumes_from_raster_layer(
    team_slug_darwin_json_v2: str,
):
    with patch(
        "darwin.exporter.formats.nifti.populate_output_volumes_from_raster_layer"
    ) as mock:
        with tempfile.TemporaryDirectory() as tmpdir:
            with ZipFile("tests/data.zip") as zfile:
                zfile.extractall(tmpdir)
            annotations_dir = (
                Path(tmpdir)
                / team_slug_darwin_json_v2
                / "nifti/releases/latest/annotations"
            )
            video_annotation_filepaths = [annotations_dir / "mask_only.json"]
            video_annotations = list(
                darwin_to_dt_gen(video_annotation_filepaths, False)
            )
            nifti.export(video_annotations, output_dir=Path(tmpdir))
            mock.assert_called()


def test_export_creates_file_for_polygons_and_masks(
    team_slug_darwin_json_v2: str,
):
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile("tests/data.zip") as zfile:
            zfile.extractall(tmpdir)
            annotations_dir = (
                Path(tmpdir)
                / team_slug_darwin_json_v2
                / "nifti/releases/latest/annotations"
            )
            video_annotation_files = {
                "mask_only.json": [
                    Path("mask_only/0/hippocampus_multislot_3_test_hippo_LOIN_m.nii.gz")
                ],
                "polygon_only.json": [
                    Path(
                        "polygon_only/0/hippocampus_multislot_3_test_hippo_create_class_1.nii.gz"
                    ),
                ],
                "polygon_and_mask.json": [
                    Path(
                        "polygon_and_mask/0/hippocampus_multislot_3_test_hippo_create_class_1.nii.gz"
                    ),
                    Path(
                        "polygon_and_mask/0/hippocampus_multislot_3_test_hippo_LOIN_m.nii.gz"
                    ),
                ],
                "empty.json": [
                    Path("empty/0/hippocampus_multislot_3_test_hippo_.nii.gz")
                ],
            }
            for video_annotation_file in video_annotation_files:
                video_annotation_filepaths = [annotations_dir / video_annotation_file]
                video_annotations = list(
                    darwin_to_dt_gen(video_annotation_filepaths, False)
                )
                nifti.export(video_annotations, output_dir=Path(tmpdir))
                for output_file in video_annotation_files[video_annotation_file]:
                    assert (
                        Path(tmpdir) / output_file
                    ).exists(), (
                        f"Expected file {output_file} does not exist in {tmpdir}"
                    )
                # Empty the directory for the next test
                for output_file in video_annotation_files[video_annotation_file]:
                    (Path(tmpdir) / output_file).unlink()


def test_shift_polygon_coords_no_scaling():
    """Test polygon coordinate shifting where all pixdims values are 1.0."""
    polygon = [{"x": 10.0, "y": 20.0}, {"x": 30.0, "y": 40.0}, {"x": 50.0, "y": 60.0}]
    pixdim = [1.0, 1.0, 1.0]
    result = nifti.shift_polygon_coords(polygon, pixdim, "AXIAL", legacy=False)
    expected = [{"x": 20.0, "y": 10.0}, {"x": 40.0, "y": 30.0}, {"x": 60.0, "y": 50.0}]
    assert result == expected


def test_shift_polygon_coords_axial_plane():
    """Test polygon coordinate shifting in axial plane."""
    polygon = [{"x": 10.0, "y": 20.0}, {"x": 30.0, "y": 40.0}, {"x": 50.0, "y": 60.0}]
    pixdim = [0.25, 0.5, 2.0]
    result = nifti.shift_polygon_coords(polygon, pixdim, "AXIAL", legacy=False)
    expected = [
        {"x": 40.0, "y": 40.0},
        {"x": 80.0, "y": 120.0},
        {"x": 120.0, "y": 200.0},
    ]
    assert result == expected


def test_shift_polygon_coords_coronal_plane():
    """Test polygon coordinate shifting in coronal plane."""
    polygon = [{"x": 10.0, "y": 20.0}, {"x": 30.0, "y": 40.0}, {"x": 50.0, "y": 60.0}]
    pixdim = [0.25, 0.5, 2.0]
    result = nifti.shift_polygon_coords(polygon, pixdim, "CORONAL", legacy=False)
    expected = [
        {"x": 10.0, "y": 40.0},
        {"x": 20.0, "y": 120.0},
        {"x": 30.0, "y": 200.0},
    ]
    assert result == expected


def test_shift_polygon_coords_sagittal_plane():
    """Test polygon coordinate shifting in sagittal plane."""
    polygon = [{"x": 10.0, "y": 20.0}, {"x": 30.0, "y": 40.0}, {"x": 50.0, "y": 60.0}]
    pixdim = [0.25, 0.5, 2.0]
    result = nifti.shift_polygon_coords(polygon, pixdim, "SAGITTAL", legacy=False)
    expected = [
        {"x": 10.0, "y": 20.0},
        {"x": 20.0, "y": 60.0},
        {"x": 30.0, "y": 100.0},
    ]
    assert result == expected


def test_shift_polygon_coords_legacy():
    """Test polygon coordinate shifting with legacy mode."""
    # Test case where pixdim[1] > pixdim[0]
    polygon = [{"x": 10.0, "y": 20.0}, {"x": 30.0, "y": 40.0}, {"x": 50.0, "y": 60.0}]
    pixdim = [0.25, 0.5, 2.0]
    result = nifti.shift_polygon_coords(polygon, pixdim, "AXIAL", legacy=True)
    expected = [{"x": 20.0, "y": 20.0}, {"x": 40.0, "y": 60.0}, {"x": 60.0, "y": 100.0}]
    assert result == expected

    # Test case where pixdim[1] < pixdim[0]
    polygon = [{"x": 10.0, "y": 20.0}, {"x": 30.0, "y": 40.0}, {"x": 50.0, "y": 60.0}]
    pixdim = [0.5, 0.25, 2.0]
    result = nifti.shift_polygon_coords(polygon, pixdim, "AXIAL", legacy=True)
    expected = [{"x": 40.0, "y": 10.0}, {"x": 80.0, "y": 30.0}, {"x": 120.0, "y": 50.0}]
    assert result == expected

    # Test case where pixdim[1] == pixdim[0]
    polygon = [{"x": 10.0, "y": 20.0}, {"x": 30.0, "y": 40.0}, {"x": 50.0, "y": 60.0}]
    pixdim = [0.5, 0.5, 2.0]
    result = nifti.shift_polygon_coords(polygon, pixdim, "AXIAL", legacy=True)
    expected = [{"x": 20.0, "y": 10.0}, {"x": 40.0, "y": 30.0}, {"x": 60.0, "y": 50.0}]
    assert result == expected


def test_global_mask_id_mapping():
    """
    Test that `populate_output_volumes_from_raster_layer` creates a global mapping
    for mask ids when the same local id is used for different mask annotations across frames.
    This verifies that mask annotations with the same local ID but from different frames
    are treated as different annotations.
    """
    annotation = MagicMock(spec=dt.Annotation)
    annotation.slot_names = ["slot1"]

    # Set up frames with overlapping local IDs but different mask_ids
    frame0_data = MagicMock()
    frame0_data.data = {
        "dense_rle": [
            0,
            9,
            1,
            1,
            0,
            90,
        ],
        "mask_annotation_ids_mapping": {"mask_id_1": 1},
    }

    frame1_data = MagicMock()
    frame1_data.data = {
        "dense_rle": [
            0,
            8,
            1,
            1,
            2,
            1,
            0,
            90,
        ],
        "mask_annotation_ids_mapping": {"mask_id_2": 1, "mask_id_3": 2},
    }

    annotation.frames = {0: frame0_data, 1: frame1_data}
    slot = MagicMock()
    slot.metadata = {
        "SeriesInstanceUID": "test_series_uid",
        "shape": [1, 10, 10, 2],
    }
    slot.width = 10
    slot.height = 10
    slot_map = {"slot1": slot}
    mask_id_to_classname = {
        "mask_id_1": "class1",
        "mask_id_2": "class2",
        "mask_id_3": "class3",
    }

    class_volume1 = MagicMock(spec=Volume)
    class_volume1.pixel_array = np.zeros((10, 10, 2))
    class_volume2 = MagicMock(spec=Volume)
    class_volume2.pixel_array = np.zeros((10, 10, 2))
    class_volume3 = MagicMock(spec=Volume)
    class_volume3.pixel_array = np.zeros((10, 10, 2))
    output_volumes = {
        "test_series_uid": {
            "class1": class_volume1,
            "class2": class_volume2,
            "class3": class_volume3,
        }
    }

    with patch("darwin.exporter.formats.nifti.decode_rle") as mock_decode_rle:
        mask_2d_frame0 = np.zeros((10, 10), dtype=np.uint8)
        mask_2d_frame0[0, 0] = 1

        mask_2d_frame1 = np.zeros((10, 10), dtype=np.uint8)
        mask_2d_frame1[1, 1] = 1
        mask_2d_frame1[2, 2] = 2

        mock_decode_rle.side_effect = [mask_2d_frame0, mask_2d_frame1]

        _ = populate_output_volumes_from_raster_layer(
            annotation=annotation,
            mask_id_to_classname=mask_id_to_classname,
            slot_map=slot_map,
            output_volumes=output_volumes,
            primary_plane="AXIAL",
        )

        # Verify results
        # Check that class1 (mask_id_1) is in frame 0 at position (0,0)
        assert class_volume1.pixel_array[0, 0, 0] == 1
        assert class_volume1.pixel_array[1, 1, 1] == 0  # Should not appear in frame 1

        # Check that class2 (mask_id_2) is in frame 1 at position (1,1) but not in frame 0
        assert class_volume2.pixel_array[0, 0, 0] == 0  # Should not appear in frame 0
        assert class_volume2.pixel_array[1, 1, 1] == 1

        # Check that class3 (mask_id_3) is in frame 1 at position (2,2) but not in frame 0
        assert class_volume3.pixel_array[0, 0, 0] == 0  # Should not appear in frame 0
        assert class_volume3.pixel_array[2, 2, 1] == 1

        # Check that no cross-contamination happened due to the shared local IDs
        # If the bug exists, class2 would appear in frame 0 because it shares local ID 1 with class1
        assert np.sum(class_volume1.pixel_array[:, :, 1]) == 0  # class1 only in frame 0
        assert np.sum(class_volume2.pixel_array[:, :, 0]) == 0  # class2 only in frame 1
        assert np.sum(class_volume3.pixel_array[:, :, 0]) == 0  # class3 only in frame 1
