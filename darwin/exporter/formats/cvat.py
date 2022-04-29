import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from xml.etree.ElementTree import Element, SubElement, tostring

import deprecation

import darwin.datatypes as dt
from darwin.version import __version__

DEPRECATION_MESSAGE = """

This function is going to be turned into private. This means that breaking 
changes in its interface and implementation are to be expected. We encourage using ``export`` 
instead of calling this low-level function directly.

"""


def export(annotation_files: Iterator[dt.AnnotationFile], output_dir: Path) -> None:
    """
    Exports the given ``AnnotationFile``s into the cvat format inside of the given ``output_dir``.

    Parameters
    ----------
    annotation_files : Iterator[dt.AnnotationFile]
        The ``AnnotationFile``\\s to be exported.
    output_dir : Path
        The folder where the new cvat file will be.
    """
    output = _build_xml(list(annotation_files))
    # TODO, maybe an optional output name (like the dataset name if available)
    output_file_path = (output_dir / "output").with_suffix(".xml")
    with open(output_file_path, "wb") as f:
        f.write(tostring(output))


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def add_subelement_text(parent: Element, name: str, value: Any) -> Element:
    sub = SubElement(parent, name)
    sub.text = str(value)
    return sub


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_xml(annotation_files: List[dt.AnnotationFile]) -> Element:
    label_lookup: Dict[str, int] = build_label_lookup(annotation_files)
    root: Element = Element("annotations")
    add_subelement_text(root, "version", "1.1")
    build_meta(root, annotation_files, label_lookup)
    build_images(root, annotation_files, label_lookup)
    return root


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_images(root: Element, annotation_files: List[dt.AnnotationFile], label_lookup: Dict[str, int]) -> None:
    for id, annotation_file in enumerate(annotation_files, 1):
        image = SubElement(root, "image")
        image.attrib["id"] = str(id)
        image.attrib["name"] = annotation_file.filename
        image.attrib["width"] = str(annotation_file.image_width)
        image.attrib["height"] = str(annotation_file.image_height)

        for annotation in annotation_file.annotations:
            build_annotation(image, annotation)


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_annotation(image: Element, annotation: dt.Annotation) -> None:
    if annotation.annotation_class.annotation_type == "bounding_box":
        box = SubElement(image, "box")
        box.attrib["label"] = annotation.annotation_class.name
        box.attrib["xtl"] = str(annotation.data["x"])
        box.attrib["ytl"] = str(annotation.data["y"])
        box.attrib["xbr"] = str(annotation.data["x"] + annotation.data["w"])
        box.attrib["ybr"] = str(annotation.data["y"] + annotation.data["h"])
        box.attrib["occluded"] = "0"
        build_attributes(box, annotation)
    else:
        print(f"[warning] skipping {annotation.annotation_class.annotation_type}")


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_attributes(box: Element, annotation: dt.Annotation) -> None:
    annotation_text: Optional[dt.SubAnnotation] = annotation.get_sub("text")
    if annotation_text:
        attribute = add_subelement_text(box, "attribute", annotation_text.data)
        attribute.attrib["name"] = "__text"

    annotation_instance_id: Optional[dt.SubAnnotation] = annotation.get_sub("instance_id")
    if annotation_instance_id:
        attribute = add_subelement_text(box, "attribute", str(annotation_instance_id.data))
        attribute.attrib["name"] = "__instance_id"

    annotation_attributes: Optional[dt.SubAnnotation] = annotation.get_sub("attributes")
    if annotation_attributes:
        for attrib in annotation_attributes.data:
            attribute = add_subelement_text(box, "attribute", "")
            attribute.attrib["name"] = attrib


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_meta(root: Element, annotation_files: List[dt.AnnotationFile], label_lookup: Dict[str, int]) -> None:
    meta: Element = SubElement(root, "meta")
    add_subelement_text(meta, "dumped", str(datetime.datetime.now(tz=datetime.timezone.utc)))

    task: Element = SubElement(meta, "task")
    add_subelement_text(task, "id", 1)
    add_subelement_text(task, "name", "exported_task_from_darwin")
    add_subelement_text(task, "size", len(annotation_files))
    add_subelement_text(task, "mode", "annotation")
    add_subelement_text(task, "overlapp", 0)
    add_subelement_text(task, "bugtracker", None)
    add_subelement_text(task, "flipped", False)
    add_subelement_text(task, "created", str(datetime.datetime.now(tz=datetime.timezone.utc)))
    add_subelement_text(task, "updated", str(datetime.datetime.now(tz=datetime.timezone.utc)))

    labels: Element = SubElement(task, "labels")
    build_labels(labels, label_lookup)

    segments: Element = SubElement(task, "segments")
    build_segments(segments, annotation_files)

    owner: Element = SubElement(task, "owner")
    add_subelement_text(owner, "username", "example_username")
    add_subelement_text(owner, "email", "user@example.com")


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_segments(segments: Element, annotation_files: List[dt.AnnotationFile]) -> None:
    segment: Element = SubElement(segments, "segment")
    add_subelement_text(segment, "id", 1)
    add_subelement_text(segment, "start", 1)
    add_subelement_text(segment, "end", len(annotation_files))
    add_subelement_text(segment, "url", "not applicable")


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_labels(labels: Element, label_lookup: Dict[str, int]) -> None:
    for key in label_lookup.keys():
        label: Element = SubElement(labels, "label")
        add_subelement_text(label, "name", key)
        SubElement(label, "attributes")


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_label_lookup(annotation_files: List[dt.AnnotationFile]) -> Dict[str, int]:
    labels: Dict[str, int] = {}
    for annotation_file in annotation_files:
        for annotation_class in annotation_file.annotation_classes:
            if annotation_class.name not in labels and annotation_class.annotation_type == "bounding_box":
                labels[annotation_class.name] = len(labels)
    return labels


def _add_subelement_text(parent: Element, name: str, value: Any) -> Element:
    sub = SubElement(parent, name)
    sub.text = str(value)
    return sub


def _build_xml(annotation_files: List[dt.AnnotationFile]) -> Element:
    label_lookup: Dict[str, int] = _build_label_lookup(annotation_files)
    root: Element = Element("annotations")
    _add_subelement_text(root, "version", "1.1")
    _build_meta(root, annotation_files, label_lookup)
    _build_images(root, annotation_files, label_lookup)
    return root


def _build_images(root: Element, annotation_files: List[dt.AnnotationFile], label_lookup: Dict[str, int]) -> None:
    for id, annotation_file in enumerate(annotation_files, 1):
        image = SubElement(root, "image")
        image.attrib["id"] = str(id)
        image.attrib["name"] = annotation_file.filename
        image.attrib["width"] = str(annotation_file.image_width)
        image.attrib["height"] = str(annotation_file.image_height)

        for annotation in annotation_file.annotations:
            _build_annotation(image, annotation)


def _build_annotation(image: Element, annotation: dt.Annotation) -> None:
    if annotation.annotation_class.annotation_type == "bounding_box":
        box = SubElement(image, "box")
        box.attrib["label"] = annotation.annotation_class.name
        box.attrib["xtl"] = str(annotation.data["x"])
        box.attrib["ytl"] = str(annotation.data["y"])
        box.attrib["xbr"] = str(annotation.data["x"] + annotation.data["w"])
        box.attrib["ybr"] = str(annotation.data["y"] + annotation.data["h"])
        box.attrib["occluded"] = "0"
        _build_attributes(box, annotation)
    else:
        print(f"[warning] skipping {annotation.annotation_class.annotation_type}")


def _build_attributes(box: Element, annotation: dt.Annotation) -> None:
    annotation_text: Optional[dt.SubAnnotation] = annotation.get_sub("text")
    if annotation_text:
        attribute = _add_subelement_text(box, "attribute", annotation_text.data)
        attribute.attrib["name"] = "__text"

    annotation_instance_id: Optional[dt.SubAnnotation] = annotation.get_sub("instance_id")
    if annotation_instance_id:
        attribute = _add_subelement_text(box, "attribute", str(annotation_instance_id.data))
        attribute.attrib["name"] = "__instance_id"

    annotation_attributes: Optional[dt.SubAnnotation] = annotation.get_sub("attributes")
    if annotation_attributes:
        for attrib in annotation_attributes.data:
            attribute = _add_subelement_text(box, "attribute", "")
            attribute.attrib["name"] = attrib


def _build_meta(root: Element, annotation_files: List[dt.AnnotationFile], label_lookup: Dict[str, int]) -> None:
    meta: Element = SubElement(root, "meta")
    _add_subelement_text(meta, "dumped", str(datetime.datetime.now(tz=datetime.timezone.utc)))

    task: Element = SubElement(meta, "task")
    _add_subelement_text(task, "id", 1)
    _add_subelement_text(task, "name", "exported_task_from_darwin")
    _add_subelement_text(task, "size", len(annotation_files))
    _add_subelement_text(task, "mode", "annotation")
    _add_subelement_text(task, "overlapp", 0)
    _add_subelement_text(task, "bugtracker", None)
    _add_subelement_text(task, "flipped", False)
    _add_subelement_text(task, "created", str(datetime.datetime.now(tz=datetime.timezone.utc)))
    _add_subelement_text(task, "updated", str(datetime.datetime.now(tz=datetime.timezone.utc)))

    labels: Element = SubElement(task, "labels")
    _build_labels(labels, label_lookup)

    segments: Element = SubElement(task, "segments")
    _build_segments(segments, annotation_files)

    owner: Element = SubElement(task, "owner")
    _add_subelement_text(owner, "username", "example_username")
    _add_subelement_text(owner, "email", "user@example.com")


def _build_segments(segments: Element, annotation_files: List[dt.AnnotationFile]) -> None:
    segment: Element = SubElement(segments, "segment")
    _add_subelement_text(segment, "id", 1)
    _add_subelement_text(segment, "start", 1)
    _add_subelement_text(segment, "end", len(annotation_files))
    _add_subelement_text(segment, "url", "not applicable")


def _build_labels(labels: Element, label_lookup: Dict[str, int]) -> None:
    for key in label_lookup.keys():
        label: Element = SubElement(labels, "label")
        _add_subelement_text(label, "name", key)
        SubElement(label, "attributes")


def _build_label_lookup(annotation_files: List[dt.AnnotationFile]) -> Dict[str, int]:
    labels: Dict[str, int] = {}
    for annotation_file in annotation_files:
        for annotation_class in annotation_file.annotation_classes:
            if annotation_class.name not in labels and annotation_class.annotation_type == "bounding_box":
                labels[annotation_class.name] = len(labels)
    return labels
