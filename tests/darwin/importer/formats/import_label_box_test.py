from pathlib import Path
from typing import List, Optional

import pytest
from darwin.datatypes import Annotation, AnnotationClass, AnnotationFile
from darwin.importer.formats.label_box import parse_file


def describe_parse_file():
    @pytest.fixture
    def file_path(tmp_path: Path):
        path = tmp_path / "annotation.json"
        yield path
        path.unlink()

    def test_it_returns_none_if_there_are_no_annotations():
        path = Path("path/to/file.xml")
        assert parse_file(path) is None

    def test_it_raises_if_external_id_is_missing(file_path: Path):
        json: str = """
         [
            {
               "Label":{
                  "objects":[
                     {
                        "title":"Fruit",
                        "bbox":{
                           "top":3558,
                           "left":145,
                           "height":623,
                           "width":449
                        }
                     }
                  ]
               }
            }
         ]
        """

        file_path.write_text(json)

        with pytest.raises(ValueError) as error:
            parse_file(file_path)

        assert f"LabelBox Object must have an 'External ID' key" in str(error.value)

    def test_it_raises_if_label_is_missing(file_path: Path):
        json: str = """
         [{"External ID": "flowers.jpg"}]
        """

        file_path.write_text(json)

        with pytest.raises(ValueError) as error:
            parse_file(file_path)

        assert f"LabelBox Object must have a 'Label' key" in str(error.value)

    def test_it_raises_if_label_objects_is_missing(file_path: Path):
        json: str = """
         [{"External ID": "flowers.jpg", "Label": {}}]
        """

        file_path.write_text(json)

        with pytest.raises(ValueError) as error:
            parse_file(file_path)

        assert f"LabelBox Label must have an 'objects' key" in str(error.value)

    def test_it_raises_if_label_object_has_unknown_format(file_path: Path):
        json: str = """
         [{
               "Label":{
                  "objects":[{"title":"Fruit", "unkown_annotation": 0}]
               },
               "External ID": "demo-image-7.jpg"
            }]
        """

        file_path.write_text(json)

        with pytest.raises(ValueError) as error:
            parse_file(file_path)

        assert f"Unsupported object type" in str(error.value)

    def test_it_raises_if_annotation_has_no_title(file_path: Path):
        json: str = """
         [
            {
               "Label":{
                  "objects":[
                     {
                        "bbox":{
                           "top":3558,
                           "left":145,
                           "height":623,
                           "width":449
                        }
                     }
                  ]
               },
               "External ID": "demo-image-7.jpg"
            }
         ]
        """

        file_path.write_text(json)

        with pytest.raises(ValueError) as error:
            parse_file(file_path)

        assert f"LabelBox objects must have a title" in str(error.value)

    def test_it_imports_bboxes(file_path: Path):
        json: str = """
         [
            {
               "Label":{
                  "objects":[
                     {
                        "title":"Fruit",
                        "bbox":{
                           "top":3558,
                           "left":145,
                           "height":623,
                           "width":449
                        }
                     }
                  ]
               },
               "External ID": "demo-image-7.jpg"
            }
         ]
        """

        file_path.write_text(json)

        annotation_files: Optional[List[AnnotationFile]] = parse_file(file_path)
        assert annotation_files is not None

        annotation_file: AnnotationFile = annotation_files.pop()
        assert annotation_file.path == file_path
        assert annotation_file.filename == "demo-image-7.jpg"
        assert annotation_file.annotation_classes

        assert annotation_file.annotations
        bbox_annotation = annotation_file.annotations.pop()
        assert_bbox(bbox_annotation, 3558, 145, 623, 449)

        annotation_class = bbox_annotation.annotation_class
        assert_annotation_class(annotation_class, "Fruit", "bounding_box")


def assert_bbox(annotation: Annotation, x: float, y: float, h: float, w: float) -> None:
    data = annotation.data

    assert data
    assert data.get("x") == x
    assert data.get("y") == y
    assert data.get("w") == w
    assert data.get("h") == h


def assert_annotation_class(
    annotation_class: AnnotationClass, name: str, type: str, internal_type: Optional[str] = None
) -> None:
    assert annotation_class
    assert annotation_class.name == name
    assert annotation_class.annotation_type == type
    assert annotation_class.annotation_internal_type == internal_type

