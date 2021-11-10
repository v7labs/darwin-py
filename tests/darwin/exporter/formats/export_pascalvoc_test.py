from pathlib import Path
from xml.etree.ElementTree import Element, tostring

from darwin.datatypes import Annotation, AnnotationClass, AnnotationFile
from darwin.exporter.formats.pascalvoc import build_xml


def describe_build_xml():
    def test_returns_bounding_boxes_of_polygons():
        car_class = AnnotationClass(name="car", annotation_type="polygon", annotation_internal_type=None)
        car_annotation = Annotation(
            annotation_class=car_class,
            data={"path": [{...}], "bounding_box": {"x": 94.0, "y": 438.0, "w": 1709.0, "h": 545.0},},
            subs=[],
        )
        annotation_file = AnnotationFile(
            path=Path("/annotation_test.json"),
            filename="annotation_test.jpg",
            annotation_classes={car_class},
            annotations=[car_annotation],
            frame_urls=None,
            image_height=1080,
            image_width=1920,
            is_video=False,
        )

        xml = build_xml(annotation_file)

        assert isinstance(xml.find("object"), Element)
