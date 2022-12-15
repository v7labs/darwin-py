from pathlib import Path
from typing import Any, Dict, Iterable
from xml.etree.ElementTree import Element, SubElement, tostring

import deprecation
import orjson as json

import darwin.datatypes as dt
from darwin.version import __version__

DEPRECATION_MESSAGE = """

This function is going to be turned into private. This means that breaking 
changes in its interface and implementation are to be expected. We encourage using ``export`` 
instead of calling this low-level function directly.

"""

REMOVAL_MESSAGE = """

This function is going to be removed. This means that breaking 
changes in its interface and implementation are to be expected. We encourage no longer using it.

"""


def export(annotation_files: Iterable[dt.AnnotationFile], output_dir: Path) -> None:
    """
    Exports the given ``AnnotationFile``\\s into the pascalvoc format inside of the given
    ``output_dir``.

    Parameters
    ----------
    annotation_files : Iterable[dt.AnnotationFile]
        The ``AnnotationFile``\\s to be exported.
    output_dir : Path
        The folder where the new pascalvoc files will be.
    """
    for annotation_file in annotation_files:
        _export_file(annotation_file, output_dir)


@deprecation.deprecated(
    deprecated_in="0.7.10",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def export_file(annotation_file: dt.AnnotationFile, output_dir: Path) -> None:
    xml = build_xml(annotation_file)
    output_file_path = (output_dir / annotation_file.filename).with_suffix(".xml")
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file_path, "wb") as f:
        f.write(tostring(xml))


@deprecation.deprecated(
    deprecated_in="0.7.10",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_xml(annotation_file: dt.AnnotationFile) -> Element:
    root: Element = Element("annotation")
    add_subelement_text(root, "folder", "images")
    add_subelement_text(root, "filename", annotation_file.filename)
    add_subelement_text(root, "path", f"images/{annotation_file.filename}")

    source = SubElement(root, "source")
    add_subelement_text(source, "database", "darwin")

    size = SubElement(root, "size")
    add_subelement_text(size, "width", str(annotation_file.image_width))
    add_subelement_text(size, "height", str(annotation_file.image_height))
    add_subelement_text(size, "depth", "3")

    add_subelement_text(root, "segmented", "0")

    for annotation in annotation_file.annotations:
        annotation_type = annotation.annotation_class.annotation_type
        if annotation_type not in ["bounding_box", "polygon", "complex_polygon"]:
            continue

        data = annotation.data
        sub_annotation = SubElement(root, "object")
        add_subelement_text(sub_annotation, "name", annotation.annotation_class.name)
        add_subelement_text(sub_annotation, "pose", "Unspecified")
        add_subelement_text(sub_annotation, "truncated", "0")
        add_subelement_text(sub_annotation, "difficult", "0")
        bndbox = SubElement(sub_annotation, "bndbox")

        if annotation_type == "polygon" or annotation_type == "complex_polygon":
            data = data.get("bounding_box")

        xmin = data.get("x")
        ymin = data.get("y")
        xmax = xmin + data.get("w")
        ymax = ymin + data.get("h")
        add_subelement_text(bndbox, "xmin", str(round(xmin)))
        add_subelement_text(bndbox, "ymin", str(round(ymin)))
        add_subelement_text(bndbox, "xmax", str(round(xmax)))
        add_subelement_text(bndbox, "ymax", str(round(ymax)))

    return root


@deprecation.deprecated(
    deprecated_in="0.7.10",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def add_subelement_text(parent: Element, name: str, value: Any) -> Element:
    sub: Element = SubElement(parent, name)
    sub.text = value
    return sub


@deprecation.deprecated(
    deprecated_in="0.7.10",
    removed_in="0.8.0",
    current_version=__version__,
    details=REMOVAL_MESSAGE,
)
def convert_file(path: Path) -> Element:
    with open(path, "r") as f:
        data = json.loads(f.read())
        return build_voc(data["image"], data["annotations"])


@deprecation.deprecated(
    deprecated_in="0.7.10",
    removed_in="0.8.0",
    current_version=__version__,
    details=REMOVAL_MESSAGE,
)
def save_xml(xml: Element, path: Path) -> None:
    with open(path, "wb") as f:
        f.write(tostring(xml))


@deprecation.deprecated(
    deprecated_in="0.7.10",
    removed_in="0.8.0",
    current_version=__version__,
    details=REMOVAL_MESSAGE,
)
def build_voc(metadata: Dict[str, Any], annotations: Iterable[Dict[str, Any]]) -> Element:
    print(metadata)
    root: Element = Element("annotation")
    add_subelement_text(root, "folder", "images")
    add_subelement_text(root, "filename", metadata["original_filename"])
    add_subelement_text(root, "path", f"images/{metadata['original_filename']}")

    source: Element = SubElement(root, "source")
    add_subelement_text(source, "database", "darwin")

    size: Element = SubElement(root, "size")
    add_subelement_text(size, "width", str(metadata["width"]))
    add_subelement_text(size, "height", str(metadata["height"]))
    add_subelement_text(size, "depth", "3")

    add_subelement_text(root, "segmented", "0")

    for annotation in annotations:
        if "bounding_box" not in annotation:
            continue
        data = annotation["bounding_box"]
        sub_annotation = SubElement(root, "object")
        add_subelement_text(sub_annotation, "name", annotation["name"])
        add_subelement_text(sub_annotation, "pose", "Unspecified")
        add_subelement_text(sub_annotation, "truncated", "0")
        add_subelement_text(sub_annotation, "difficult", "0")
        bndbox = SubElement(sub_annotation, "bndbox")
        add_subelement_text(bndbox, "xmin", str(round(data["x"])))
        add_subelement_text(bndbox, "ymin", str(round(data["y"])))
        add_subelement_text(bndbox, "xmax", str(round(data["x"] + data["w"])))
        add_subelement_text(bndbox, "ymax", str(round(data["y"] + data["h"])))

    return root


######################################


def _export_file(annotation_file: dt.AnnotationFile, output_dir: Path) -> None:
    xml = _build_xml(annotation_file)
    output_file_path = (output_dir / annotation_file.filename).with_suffix(".xml")
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file_path, "wb") as f:
        f.write(tostring(xml))


def _build_xml(annotation_file: dt.AnnotationFile) -> Element:
    root: Element = Element("annotation")
    _add_subelement_text(root, "folder", "images")
    _add_subelement_text(root, "filename", annotation_file.filename)
    _add_subelement_text(root, "path", f"images/{annotation_file.filename}")

    source = SubElement(root, "source")
    _add_subelement_text(source, "database", "darwin")

    size = SubElement(root, "size")
    _add_subelement_text(size, "width", str(annotation_file.image_width))
    _add_subelement_text(size, "height", str(annotation_file.image_height))
    _add_subelement_text(size, "depth", "3")

    _add_subelement_text(root, "segmented", "0")

    for annotation in annotation_file.annotations:
        annotation_type = annotation.annotation_class.annotation_type
        if annotation_type not in ["bounding_box", "polygon", "complex_polygon"]:
            continue

        data = annotation.data
        sub_annotation = SubElement(root, "object")
        _add_subelement_text(sub_annotation, "name", annotation.annotation_class.name)
        _add_subelement_text(sub_annotation, "pose", "Unspecified")
        _add_subelement_text(sub_annotation, "truncated", "0")
        _add_subelement_text(sub_annotation, "difficult", "0")
        bndbox = SubElement(sub_annotation, "bndbox")

        if annotation_type == "polygon" or annotation_type == "complex_polygon":
            data = data.get("bounding_box")

        xmin = data.get("x")
        ymin = data.get("y")
        xmax = xmin + data.get("w")
        ymax = ymin + data.get("h")
        _add_subelement_text(bndbox, "xmin", str(round(xmin)))
        _add_subelement_text(bndbox, "ymin", str(round(ymin)))
        _add_subelement_text(bndbox, "xmax", str(round(xmax)))
        _add_subelement_text(bndbox, "ymax", str(round(ymax)))

    return root


def _add_subelement_text(parent: Element, name: str, value: Any) -> Element:
    sub: Element = SubElement(parent, name)
    sub.text = value
    return sub
