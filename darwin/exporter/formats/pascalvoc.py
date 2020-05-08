import json
import xml.etree.ElementTree as ET


def export(annotation_files, output_dir):
    for annotation_file in annotation_files:
        export_file(annotation_file, output_dir)


def export_file(annotation_file, output_dir):
    xml = build_xml(annotation_file)
    output_file_path = (output_dir / annotation_file.filename).with_suffix(".xml")
    with open(output_file_path, "wb") as f:
        f.write(ET.tostring(xml))


def build_xml(annotation_file):
    root = ET.Element("annotation")
    add_subelement_text(root, "folder", "images")
    add_subelement_text(root, "filename", annotation_file.filename)
    add_subelement_text(root, "path", f"images/{annotation_file.filename}")

    source = ET.SubElement(root, "source")
    add_subelement_text(source, "database", "darwin")

    size = ET.SubElement(root, "size")
    add_subelement_text(size, "width", str(annotation_file.image_width))
    add_subelement_text(size, "height", str(annotation_file.image_height))
    add_subelement_text(size, "depth", "3")

    add_subelement_text(root, "segmented", "0")

    for annotation in annotation_file.annotations:
        if annotation.annotation_class.annotation_type != "bounding_box":
            continue
        data = annotation.data
        sub_annotation = ET.SubElement(root, "object")
        add_subelement_text(sub_annotation, "name", annotation.annotation_class.name)
        add_subelement_text(sub_annotation, "pose", "Unspecified")
        add_subelement_text(sub_annotation, "truncated", "0")
        add_subelement_text(sub_annotation, "difficult", "0")
        bndbox = ET.SubElement(sub_annotation, "bndbox")
        add_subelement_text(bndbox, "xmin", str(round(data["x"])))
        add_subelement_text(bndbox, "ymin", str(round(data["y"])))
        add_subelement_text(bndbox, "xmax", str(round(data["x"] + data["w"])))
        add_subelement_text(bndbox, "ymax", str(round(data["y"] + data["h"])))
    return root


def add_subelement_text(parent, name, value):
    sub = ET.SubElement(parent, name)
    sub.text = value
    return sub


def convert_file(path):
    with open(path, "r") as f:
        data = json.load(f)
        return build_voc(data["image"], data["annotations"])


def save_xml(xml, path):
    with open(path, "wb") as f:
        f.write(ET.tostring(xml))


def build_voc(metadata, annotations):
    print(metadata)
    root = ET.Element("annotation")
    add_subelement_text(root, "folder", "images")
    add_subelement_text(root, "filename", metadata["original_filename"])
    add_subelement_text(root, "path", f"images/{metadata['original_filename']}")

    source = ET.SubElement(root, "source")
    add_subelement_text(source, "database", "darwin")

    size = ET.SubElement(root, "size")
    add_subelement_text(size, "width", str(metadata["width"]))
    add_subelement_text(size, "height", str(metadata["height"]))
    add_subelement_text(size, "depth", "3")

    add_subelement_text(root, "segmented", "0")

    for annotation in annotations:
        if "bounding_box" not in annotation:
            continue
        data = annotation["bounding_box"]
        sub_annotation = ET.SubElement(root, "object")
        add_subelement_text(sub_annotation, "name", annotation["name"])
        add_subelement_text(sub_annotation, "pose", "Unspecified")
        add_subelement_text(sub_annotation, "truncated", "0")
        add_subelement_text(sub_annotation, "difficult", "0")
        bndbox = ET.SubElement(sub_annotation, "bndbox")
        add_subelement_text(bndbox, "xmin", str(round(data["x"])))
        add_subelement_text(bndbox, "ymin", str(round(data["y"])))
        add_subelement_text(bndbox, "xmax", str(round(data["x"] + data["w"])))
        add_subelement_text(bndbox, "ymax", str(round(data["y"] + data["h"])))
    return root
