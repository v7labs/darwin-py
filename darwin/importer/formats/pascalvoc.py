import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import darwin.datatypes as dt


def parse_file(path: Path) -> Optional[dt.AnnotationFile]:
    if path.suffix != ".xml":
        return

    tree = ET.parse(path)
    root = tree.getroot()
    filename = root.find("filename").text
    annotations = list(filter(None, map(_parse_annotation, root.findall("object"))))
    annotation_classes = set([annotation.annotation_class for annotation in annotations])
    return dt.AnnotationFile(path, filename, annotation_classes, annotations)


def _parse_annotation(annotation_object):
    class_name = annotation_object.find("name").text
    bndbox = annotation_object.find("bndbox")
    xmin = int(bndbox.find("xmin").text)
    xmax = int(bndbox.find("xmax").text)
    ymin = int(bndbox.find("ymin").text)
    ymax = int(bndbox.find("ymax").text)

    return dt.make_bounding_box(class_name, xmin, ymin, xmax - xmin, ymax - ymin)
