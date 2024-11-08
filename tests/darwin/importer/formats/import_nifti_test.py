import argparse
import json
import tempfile
from pathlib import Path
from typing import Union
from unittest.mock import patch
from zipfile import ZipFile

import numpy as np
import pytest
from scipy import ndimage
import nibabel as nib

from darwin.datatypes import (
    Annotation,
    AnnotationClass,
    AnnotationFile,
    SubAnnotation,
    VideoAnnotation,
)
from darwin.importer.formats.nifti import get_new_axial_size, parse_path, process_nifti
from tests.fixtures import *


def test_image_annotation_nifti_import_single_slot(team_slug_darwin_json_v2: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile("tests/data.zip") as zfile:
            zfile.extractall(tmpdir)
            label_path = (
                Path(tmpdir)
                / team_slug_darwin_json_v2
                / "nifti"
                / "releases"
                / "latest"
                / "annotations"
                / "vol0_brain.nii.gz"
            )
            input_dict = {
                "data": [
                    {
                        "image": "vol0 (1).nii",
                        "label": str(label_path),
                        "class_map": {"1": "brain"},
                        "mode": "video",
                    }
                ]
            }
            upload_json = Path(tmpdir) / "annotations.json"
            upload_json.write_text(
                json.dumps(input_dict, indent=4, sort_keys=True, default=str)
            )
            annotation_files = parse_path(path=upload_json)
            annotation_file = annotation_files[0]
            output_json_string = json.loads(
                serialise_annotation_file(annotation_file, as_dict=False)
            )
            expected_json_string = json.load(
                open(
                    Path(tmpdir)
                    / team_slug_darwin_json_v2
                    / "nifti"
                    / "vol0_annotation_file.json",
                    "r",
                )
            )
            assert (
                output_json_string["annotations"][0]["frames"]
                == expected_json_string["annotations"][0]["frames"]
            )


def test_image_annotation_nifti_import_multi_slot(team_slug_darwin_json_v2: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile("tests/data.zip") as zfile:
            zfile.extractall(tmpdir)
            label_path = (
                Path(tmpdir)
                / team_slug_darwin_json_v2
                / "nifti"
                / "releases"
                / "latest"
                / "annotations"
                / "vol0_brain.nii.gz"
            )
            input_dict = {
                "data": [
                    {
                        "image": "vol0 (1).nii",
                        "label": str(label_path),
                        "class_map": {"1": "brain"},
                        "mode": "video",
                        "is_mpr": True,
                        "slot_names": ["0.3", "0.2", "0.1"],
                    }
                ]
            }
            upload_json = Path(tmpdir) / "annotations.json"
            upload_json.write_text(
                json.dumps(input_dict, indent=4, sort_keys=True, default=str)
            )

            annotation_files = parse_path(path=upload_json)
            annotation_file = annotation_files[0]
            output_json_string = json.loads(
                serialise_annotation_file(annotation_file, as_dict=False)
            )
            expected_json_string = json.load(
                open(
                    Path(tmpdir)
                    / team_slug_darwin_json_v2
                    / "nifti"
                    / "vol0_annotation_file_multi_slot.json",
                    "r",
                )
            )
            assert (
                output_json_string["annotations"][0]["frames"]
                == expected_json_string["annotations"][0]["frames"]
            )


def test_image_annotation_nifti_import_incorrect_number_slot(
    team_slug_darwin_json_v2: str,
):
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile("tests/data.zip") as zfile:
            zfile.extractall(tmpdir)
            label_path = (
                Path(tmpdir)
                / team_slug_darwin_json_v2
                / "nifti"
                / "releases"
                / "latest"
                / "annotations"
                / "vol0_brain.nii.gz"
            )
            input_dict = {
                "data": [
                    {
                        "image": "vol0 (1).nii",
                        "label": str(label_path),
                        "class_map": {"1": "brain"},
                        "mode": "video",
                        "is_mpr": True,
                        "slot_names": ["0.3", "0.2"],
                    }
                ]
            }
            upload_json = Path(tmpdir) / "annotations.json"
            upload_json.write_text(
                json.dumps(input_dict, indent=4, sort_keys=True, default=str)
            )
            with pytest.raises(Exception):
                parse_path(path=upload_json)


def test_image_annotation_nifti_import_single_slot_to_mask_legacy(
    team_slug_darwin_json_v2: str,
):
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile("tests/data.zip") as zfile:
            zfile.extractall(tmpdir)
            label_path = (
                Path(tmpdir)
                / team_slug_darwin_json_v2
                / "nifti"
                / "releases"
                / "latest"
                / "annotations"
                / "vol0_brain.nii.gz"
            )
            input_dict = {
                "data": [
                    {
                        "image": "vol0 (1).nii",
                        "label": str(label_path),
                        "class_map": {"1": "brain"},
                        "mode": "mask",
                        "is_mpr": False,
                        "slot_names": ["0.1"],
                    }
                ]
            }
            upload_json = Path(tmpdir) / "annotations.json"
            upload_json.write_text(
                json.dumps(input_dict, indent=4, sort_keys=True, default=str)
            )

            with patch("darwin.importer.formats.nifti.zoom") as mock_zoom:
                mock_zoom.side_effect = ndimage.zoom

                annotation_files = parse_path(path=upload_json, legacy=True)
                annotation_file = annotation_files[0]
                output_json_string = json.loads(
                    serialise_annotation_file(annotation_file, as_dict=False)
                )
                expected_json_string = json.load(
                    open(
                        Path(tmpdir)
                        / team_slug_darwin_json_v2
                        / "nifti"
                        / "vol0_annotation_file_to_mask.json",
                        "r",
                    )
                )
                # This needs to not check for mask_annotation_ids_mapping as these
                # are randomly generated
                [
                    frame.get("raster_layer", {}).pop("mask_annotation_ids_mapping")
                    for frame in output_json_string["annotations"][0]["frames"].values()
                ]
                [
                    frame.get("raster_layer", {}).pop("mask_annotation_ids_mapping")
                    for frame in expected_json_string["annotations"][0][
                        "frames"
                    ].values()
                ]

                assert mock_zoom.call_count == len(
                    expected_json_string["annotations"][0]["frames"]
                )
                assert (
                    output_json_string["annotations"][0]["frames"]
                    == expected_json_string["annotations"][0]["frames"]
                )


def test_get_new_axial_size():
    volume = np.zeros((10, 10, 10))
    pixdims = (1, 0.5, 0.5)
    new_size = get_new_axial_size(volume, pixdims)
    assert new_size == (10, 10)


def test_get_new_axial_size_with_isotropic():
    volume = np.zeros((10, 10, 10))
    pixdims = (1, 0.5, 0.5)
    new_size = get_new_axial_size(volume, pixdims, isotropic=True)
    assert new_size == (20, 10)


def test_process_nifti_orinetation(team_slug_darwin_json_v2):
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile("tests/data.zip") as zfile:
            zfile.extractall(tmpdir)
            filepath = (
                Path(tmpdir)
                / team_slug_darwin_json_v2
                / "nifti"
                / "releases"
                / "latest"
                / "annotations"
                / "vol0_brain.nii.gz"
            )
            lpi_ornt = [[0.0, -1.0], [1.0, -1.0], [2.0, -1.0]]
            ras_file = nib.load(filepath)
            lpi_transformed_file = nib.orientations.apply_orientation(
                ras_file.get_fdata(), lpi_ornt
            )
            processed_file, _ = process_nifti(input_data=ras_file)
            assert not np.array_equal(processed_file, ras_file._dataobj)
            assert np.array_equal(processed_file, lpi_transformed_file)


def serialise_annotation_file(
    annotation_file: AnnotationFile, as_dict
) -> Union[str, dict]:
    """
    Serialises an ``AnnotationFile`` into a string.

    Parameters
    ----------
    annotation_file : AnnotationFile
        The ``AnnotationFile`` to serialise.

    Returns
    -------
    str
        The serialised ``AnnotationFile``.
    """
    output_dict = {
        "path": str(annotation_file.path),
        "filename": annotation_file.filename,
        "annotation_classes": [
            serialise_annotation_class(ac, as_dict=True)
            for ac in annotation_file.annotation_classes
        ],
        "annotations": [
            serialise_annotation(a, as_dict=True) for a in annotation_file.annotations
        ],
        "is_video": annotation_file.is_video,
        "image_width": annotation_file.image_width,
        "image_height": annotation_file.image_height,
        "image_url": annotation_file.image_url,
        "workview_url": annotation_file.workview_url,
        "seq": annotation_file.seq,
        "frame_urls": annotation_file.frame_urls,
        "remote_path": annotation_file.remote_path,
    }

    json_string = json.dumps(
        output_dict,
        indent=4,
        sort_keys=True,
    )
    return output_dict if as_dict else json_string


def serialise_annotation(
    annotation: Union[Annotation, VideoAnnotation], as_dict
) -> Union[str, dict]:
    if isinstance(annotation, VideoAnnotation):
        return serialise_video_annotation(annotation, as_dict=as_dict)
    elif isinstance(annotation, Annotation):
        return serialise_general_annotation(annotation, as_dict=as_dict)


def serialise_general_annotation(annotation: Annotation, as_dict) -> Union[str, dict]:
    output_dict = {
        "annotation_class": annotation.annotation_class.name,
        "annotation_type": annotation.annotation_class.annotation_type,
        "data": annotation.data,
        "subs": [serialise_sub_annotation(sub) for sub in annotation.subs],
        "slot_names": annotation.slot_names,
    }
    json_string = json.dumps(
        output_dict,
        indent=4,
        sort_keys=True,
        default=str,
    )
    return output_dict if as_dict else json_string


def serialise_video_annotation(
    video_annotation: VideoAnnotation, as_dict: bool = True
) -> Union[str, dict]:
    data = video_annotation.get_data()
    output_dict = {
        "annotation_class": video_annotation.annotation_class.name,
        "annotation_type": video_annotation.annotation_class.annotation_type,
        "frames": data["frames"],
        "keyframes": video_annotation.keyframes,
        "segments": video_annotation.segments,
        "interpolated": video_annotation.interpolated,
        "slot_names": video_annotation.slot_names,
    }
    json_string = json.dumps(output_dict, indent=4, sort_keys=True, default=str)
    return output_dict if as_dict else json_string


def serialise_annotation_class(
    annotation_class: AnnotationClass, as_dict: bool = True
) -> Union[str, dict]:
    output_dict = {
        "name": annotation_class.name,
        "annotation_type": annotation_class.annotation_type,
        "annotation_internal_type": annotation_class.annotation_internal_type,
    }
    json_string = json.dumps(output_dict, indent=4, sort_keys=True, default=str)
    return output_dict if as_dict else json_string


def serialise_sub_annotation(
    sub_annotation: SubAnnotation, as_dict: bool = True
) -> Union[str, dict]:
    output_dict = {
        "type": sub_annotation.annotation_type,
        "data": sub_annotation.data,
    }
    json_string = json.dumps(
        output_dict,
        indent=4,
        sort_keys=True,
        default=str,
    )
    return output_dict if as_dict else json_string


if __name__ == "__main__":
    args = argparse.ArgumentParser(
        description="Update the serialisation of AnnotationFile with the current version."
    )
    input_json_string: str = """
    {
        "data": [
            {
                "image": "vol0 (1).nii",
                "label": "tests/v7/v7-darwin-json-v2/nifti/releases/latest/annotations/vol0_brain.nii.gz",
                "class_map": {
                    "1": "brain"
                },
                "is_mpr": true,
                "slot_names": ["0.3", "0.2", "0.1"],
                "mode": "video"
            }
        ]
    }
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "annotations.json"
        path.write_text(input_json_string)
        annotation_files = parse_path(path=path)
    if isinstance(annotation_files, list):
        annotation_file = annotation_files[0]
        output_json_string = serialise_annotation_file(annotation_file, as_dict=False)
        with open(
            Path("tests")
            / "v7"
            / "v7-darwin-json-v2"
            / "nifti"
            / "vol0_annotation_file_multi_slot.json",
            "w",
        ) as f:
            f.write(output_json_string)
