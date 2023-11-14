from pathlib import Path

from darwin.datatypes import Annotation, AnnotationClass, AnnotationFile
from darwin.exporter.formats.darwin import (
    _build_item_data,
    _build_v2_annotation_data,
    build_image_annotation,
)


def test_empty_annotation_file_v2():
    annotation_file = AnnotationFile(
        path=Path("test.json"), 
        filename="test.json", 
        annotation_classes=[], 
        annotations=[],
        dataset_name="Test Dataset"
    )

    expected_output = {
        "version": "2.0",
        "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json",
        "item": {
            "name": "test.json",
            "path": "/",
            "source_info": {
                "dataset": {"name": "Test Dataset", "slug": "test-dataset"},
                "item_id": "unknown-item-id",
                "team": {"name": None, "slug": None},
                "workview_url": None
            },
            "slots": []  # Include an empty slots list as per Darwin v2 format
        },
        "annotations": []
    }

    assert build_image_annotation(annotation_file) == expected_output



def test_complete_annotation_file_v2():
    annotation_class = AnnotationClass(name="test", annotation_type="polygon")
    annotation = Annotation(
        id="12345",
        annotation_class=annotation_class, 
        data={"paths": [[]]}, 
        subs=[]
    )

    annotation_file = AnnotationFile(
        path=Path("test.json"),
        filename="test.json",
        annotation_classes=[annotation_class],
        annotations=[annotation],
        dataset_name="Test Dataset"
    )

    expected_output = {
        "version": "2.0",
        "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json",
        "item": {
            "name": "test.json",
            "path": "/",
            "source_info": {
                "dataset": {"name": "Test Dataset", "slug": "test-dataset"},
                "item_id": "unknown-item-id",
                "team": {"name": None, "slug": None},
                "workview_url": None
            },
            "slots": []  # Include an empty slots list as per Darwin v2 format
        },
        "annotations": [_build_v2_annotation_data(annotation)]
    }

    assert build_image_annotation(annotation_file) == expected_output

