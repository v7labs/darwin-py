from pathlib import Path
from typing import Any, Iterable
from xml.etree.ElementTree import Element, SubElement, tostring


import darwin.datatypes as dt

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
        if annotation_type not in ["bounding_box", "polygon"]:
            continue

        data = annotation.data
        sub_annotation = SubElement(root, "object")
        _add_subelement_text(sub_annotation, "name", annotation.annotation_class.name)
        _add_subelement_text(sub_annotation, "pose", "Unspecified")
        _add_subelement_text(sub_annotation, "truncated", "0")
        _add_subelement_text(sub_annotation, "difficult", "0")
        bndbox = SubElement(sub_annotation, "bndbox")

        if annotation_type == "polygon":
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
