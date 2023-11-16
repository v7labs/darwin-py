import shutil
from pathlib import Path
from xml.etree.ElementTree import Element

import pytest

from darwin.datatypes import Annotation, AnnotationClass, AnnotationFile
from darwin.exporter.formats.pascalvoc import _build_xml, export


class TestExport:
    @pytest.fixture
    def folder_path(self, tmp_path: Path):
        path: Path = tmp_path / "pascal_voc_export_output_files"
        yield path
        shutil.rmtree(path)

    def test_it_creates_missing_folders(self, folder_path: Path):
        annotation_class: AnnotationClass = AnnotationClass(
            name="car", annotation_type="polygon", annotation_internal_type=None
        )
        annotation = Annotation(
            annotation_class=annotation_class,
            data={
                "path": [{...}],
                "bounding_box": {"x": 94.0, "y": 438.0, "w": 1709.0, "h": 545.0},
            },
            subs=[],
        )
        annotation_file = AnnotationFile(
            path=Path("/annotation_test.json"),
            filename="annotation_test.jpg",
            annotation_classes={annotation_class},
            annotations=[annotation],
            frame_urls=None,
            image_height=1080,
            image_width=1920,
            is_video=False,
        )

        export([annotation_file], folder_path)
        assert folder_path.exists()


class TestBuildXml:
    def test_xml_has_bounding_boxes_of_polygons(self):
        annotation_class = AnnotationClass(
            name="car", annotation_type="polygon", annotation_internal_type=None
        )
        annotation = Annotation(
            annotation_class=annotation_class,
            data={
                "path": [{...}],
                "bounding_box": {"x": 94.0, "y": 438.0, "w": 1709.0, "h": 545.0},
            },
            subs=[],
        )
        annotation_file = AnnotationFile(
            path=Path("/annotation_test.json"),
            filename="annotation_test.jpg",
            annotation_classes={annotation_class},
            annotations=[annotation],
            frame_urls=None,
            image_height=1080,
            image_width=1920,
            is_video=False,
        )

        xml = _build_xml(annotation_file)

        object = get_xml_element(xml, "object")
        assert_xml_element_text(object, "name", "car")
        assert_xml_element_text(object, "pose", "Unspecified")
        assert_xml_element_text(object, "truncated", "0")
        assert_xml_element_text(object, "difficult", "0")

        bndbox = get_xml_element(object, "bndbox")
        assert_xml_element_text(bndbox, "xmin", "94")
        assert_xml_element_text(bndbox, "ymin", "438")
        assert_xml_element_text(bndbox, "xmax", "1803")
        assert_xml_element_text(bndbox, "ymax", "983")

    def test_xml_has_bounding_boxes_of_complex_polygons(self):
        annotation_class = AnnotationClass(
            name="rubber",
            annotation_type="complex_polygon",
            annotation_internal_type="polygon",
        )
        annotation = Annotation(
            annotation_class=annotation_class,
            data={
                "paths": [{...}],
                "bounding_box": {
                    "x": 1174.28,
                    "y": 2379.17,
                    "w": 824.9000000000001,
                    "h": 843.52,
                },
            },
            subs=[],
        )

        annotation_file = AnnotationFile(
            path=Path("/annotation_test.json"),
            filename="annotation_test.jpg",
            annotation_classes={annotation_class},
            annotations=[annotation],
            frame_urls=None,
            image_height=4000,
            image_width=6000,
            is_video=False,
        )

        xml = _build_xml(annotation_file)

        object = get_xml_element(xml, "object")
        assert_xml_element_text(object, "name", "rubber")
        assert_xml_element_text(object, "pose", "Unspecified")
        assert_xml_element_text(object, "truncated", "0")
        assert_xml_element_text(object, "difficult", "0")

        bndbox = get_xml_element(object, "bndbox")
        assert_xml_element_text(bndbox, "xmin", "1174")
        assert_xml_element_text(bndbox, "ymin", "2379")
        assert_xml_element_text(bndbox, "xmax", "1999")
        assert_xml_element_text(bndbox, "ymax", "3223")

    def test_xml_has_bounding_boxes(self):
        annotation_class = AnnotationClass(
            name="tire", annotation_type="bounding_box", annotation_internal_type=None
        )
        annotation = Annotation(
            annotation_class=annotation_class,
            data={"x": 574.88, "y": 427.0, "w": 137.04, "h": 190.66},
            subs=[],
        )
        annotation_file = AnnotationFile(
            path=Path("/annotation_test.json"),
            filename="annotation_test.jpg",
            annotation_classes={annotation_class},
            annotations=[annotation],
            frame_urls=None,
            image_height=853,
            image_width=1400,
            is_video=False,
        )

        xml = _build_xml(annotation_file)

        object = get_xml_element(xml, "object")
        assert_xml_element_text(object, "name", "tire")
        assert_xml_element_text(object, "pose", "Unspecified")
        assert_xml_element_text(object, "truncated", "0")
        assert_xml_element_text(object, "difficult", "0")

        bndbox = get_xml_element(object, "bndbox")
        assert_xml_element_text(bndbox, "xmin", "575")
        assert_xml_element_text(bndbox, "ymin", "427")
        assert_xml_element_text(bndbox, "xmax", "712")
        assert_xml_element_text(bndbox, "ymax", "618")


def get_xml_element(parent: Element, key: str) -> Element:
    """
    Return the first child of the parent name whose name matches the given key.
    If no children are found, it raises.
    """
    object = parent.find(key)
    assert isinstance(object, Element)
    return object


def assert_xml_element_text(parent: Element, key: str, val: str) -> None:
    """
    Asserts if the first child with a name matching the key of the given parent element has the
    given text value.
    Raises if no children are found or if the text value is not equal.
    """
    obj = parent.find(key)
    assert isinstance(obj, Element)
    assert obj.text == val
