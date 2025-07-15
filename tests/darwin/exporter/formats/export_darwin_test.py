import tempfile
import zipfile
from pathlib import Path

from darwin.datatypes import Annotation, AnnotationClass, AnnotationFile
from darwin.exporter.formats.darwin import (
    _build_v2_annotation_data,
    build_image_annotation,
)
from darwin.utils import get_annotation_files_from_dir


def test_empty_annotation_file_v2():
    annotation_file = AnnotationFile(
        path=Path("test.json"),
        filename="test.json",
        annotation_classes=[],
        annotations=[],
        dataset_name="Test Dataset",
    )

    expected_output = {
        "version": "2.0",
        "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json",
        "item": {
            "name": "test.json",
            "path": "/",
            "source_info": {
                "dataset": {"name": "Test Dataset", "slug": "test-dataset"},
                "item_id": None,
                "team": {"name": "Test team", "slug": "test-team"},
                "workview_url": None,
            },
            "slots": [],  # Include an empty slots list as per Darwin v2 format
        },
        "annotations": [],
    }

    assert build_image_annotation(annotation_file, "Test team") == expected_output


def test_complete_annotation_file_v2():
    annotation_class = AnnotationClass(name="test", annotation_type="polygon")
    annotation = Annotation(
        id="12345", annotation_class=annotation_class, data={"paths": [[]]}, subs=[]
    )

    annotation_file = AnnotationFile(
        path=Path("test.json"),
        filename="test.json",
        annotation_classes=[annotation_class],
        annotations=[annotation],
        dataset_name="Test Dataset",
    )

    expected_output = {
        "version": "2.0",
        "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json",
        "item": {
            "name": "test.json",
            "path": "/",
            "source_info": {
                "dataset": {"name": "Test Dataset", "slug": "test-dataset"},
                "item_id": None,
                "team": {"name": "Test team", "slug": "test-team"},
                "workview_url": None,
            },
            "slots": [],  # Include an empty slots list as per Darwin v2 format
        },
        "annotations": [_build_v2_annotation_data(annotation)],
    }

    assert build_image_annotation(annotation_file, "Test team") == expected_output


def test_complete_annotation_file_with_bounding_box_and_tag_v2():
    # Annotation for a polygon
    polygon_class = AnnotationClass(name="polygon_test", annotation_type="polygon")
    polygon_annotation = Annotation(
        id="polygon_id",
        annotation_class=polygon_class,
        data={"paths": [[{"x": 10, "y": 10}, {"x": 20, "y": 20}]]},
        subs=[],
    )

    # Annotation for a bounding box
    bbox_class = AnnotationClass(name="bbox_test", annotation_type="bounding_box")
    bbox_annotation = Annotation(
        id="bbox_id",
        annotation_class=bbox_class,
        data={"h": 100, "w": 200, "x": 50, "y": 60},
        subs=[],
    )

    # Annotation for a tag
    tag_class = AnnotationClass(name="tag_test", annotation_type="tag")
    tag_annotation = Annotation(
        id="tag_id",
        annotation_class=tag_class,
        data={},  # Assuming tag annotations have empty data
        subs=[],
    )

    annotation_file = AnnotationFile(
        path=Path("test.json"),
        filename="test.json",
        annotation_classes=[polygon_class, bbox_class, tag_class],
        annotations=[polygon_annotation, bbox_annotation, tag_annotation],
        dataset_name="Test Dataset",
    )

    expected_output = {
        "version": "2.0",
        "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json",
        "item": {
            "name": "test.json",
            "path": "/",
            "source_info": {
                "dataset": {"name": "Test Dataset", "slug": "test-dataset"},
                "item_id": None,
                "team": {"name": "Test team", "slug": "test-team"},
                "workview_url": None,
            },
            "slots": [],  # Include an empty slots list as per Darwin v2 format
        },
        "annotations": [
            _build_v2_annotation_data(polygon_annotation),
            _build_v2_annotation_data(bbox_annotation),
            _build_v2_annotation_data(tag_annotation),
        ],
    }

    assert build_image_annotation(annotation_file, "Test team") == expected_output


def test_properties_metadata_is_ignored_when_reading_annotations_directory():
    with tempfile.TemporaryDirectory() as tmpdirname:
        with zipfile.ZipFile("tests/dataset_with_properties.zip", "r") as zip_ref:
            zip_ref.extractall(tmpdirname)

        annotation_filepaths = list(get_annotation_files_from_dir(Path(tmpdirname)))
        for annotation_filepath in annotation_filepaths:
            assert "./v7/" not in annotation_filepath
            assert "\\.v7\\" not in annotation_filepath
