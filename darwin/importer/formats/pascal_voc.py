import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional

import darwin.datatypes as dt


def parse_path(path: Path) -> Optional[dt.AnnotationFile]:
    """
    Parses the given pascalvoc file and maybe returns the corresponding annotation.
    The file must have the following structure:

    .. code-block:: xml

        <filename>SOME_FILE_NAME</filename>
        <object>
            <name>CLASS_NAME</name>
            <bndbox>
                <xmax>NUMBER</xmax>
                <xmin>NUMBER</xmin>
                <ymax>NUMBER</ymax>
                <ymin>NUMBER</ymin>
            </bndbox>
        </object>
        <object>
            ...
        </object>

    Parameters
    --------
    path: Path
        The path of the file to parse.

    Returns
    -------
    Optional[darwin.datatypes.AnnotationFile]
        An AnnotationFile with the parsed information from the file or None, if the file is not a
        `XML` file.

    Raises
    ------
    ValueError
        If a mandatory child element is missing or is empty. Mandatory child elements are:
        filename, name, bndbox, xmin, xmax, ymin and ymax.

    """
    if path.suffix != ".xml":
        return None

    tree = ET.parse(str(path))
    root = tree.getroot()

    filename = _find_text_value(root, "filename")

    annotations: List[dt.Annotation] = list(filter(None, map(_parse_annotation, root.findall("object"))))
    annotation_classes = set([annotation.annotation_class for annotation in annotations])

    return dt.AnnotationFile(path, filename, annotation_classes, annotations, remote_path="/")


def _parse_annotation(annotation_object: ET.Element) -> dt.Annotation:
    """
    Parses the given XML element and returns the corresponding annotation.

    Parameters
    --------
    annotation_object: xml.etree.ElementTree.Element
        The element to convert into an annotation.

    Returns
    -------
    darwin.datatypes.AnnotationFile
        An AnnotationFile with the parsed information from the XML element.

    Raises
    ------
    ValueError
        If a mandatory chield element is missing or is empty. Mandatory child elements are:
        name, bndbox, xmin, xmax, ymin and ymax.
    """
    class_name = _find_text_value(annotation_object, "name")

    bndbox = _find_element(annotation_object, "bndbox")
    xmin = int(float(_find_text_value(bndbox, "xmin")))
    xmax = int(float(_find_text_value(bndbox, "xmax")))
    ymin = int(float(_find_text_value(bndbox, "ymin")))
    ymax = int(float(_find_text_value(bndbox, "ymax")))

    return dt.make_bounding_box(class_name, xmin, ymin, xmax - xmin, ymax - ymin)


def _find_element(source: ET.Element, name: str) -> ET.Element:
    """
    Finds a child element inside the source element with the given name and returns it.

    Parameters
    --------
    source: xml.etree.ElementTree.Element
        Parent element that contains childs elements to be searched.
    name: str
        Name of the child element we wish to find.

    Returns
    -------
    xml.etree.ElementTree.Element
        Child element with the given name.

    Raises
    ------
    ValueError
        If a child element with the given name could not be found.
    """
    element = source.find(name)
    if element is None:
        raise ValueError(f"Could not find {name} element in annotation file")
    return element


def _find_text_value(source: ET.Element, name: str) -> str:
    """
    Finds a child element inside the source element with the given name and returns its text value.

    Parameters
    --------
    source: xml.etree.ElementTree.Element
        Parent element that contains childs elements to be searched.
    name: str
        Name of the child element we wish to find.

    Returns
    -------
    str
        Text value of the found child element.

    Raises
    ------
    ValueError
        If the found child element has no text value or its text value is empty.
    """
    element = _find_element(source, name)
    if element.text is None or not element.text.strip():
        raise ValueError(f"{name} element does not have a text value")
    return element.text
