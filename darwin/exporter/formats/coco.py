import json
from datetime import date
from pathlib import Path
from typing import Generator, List

import numpy as np
from upolygon import draw_polygon

import darwin.datatypes as dt
from darwin.utils import convert_polygons_to_sequences


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NumpyEncoder, self).default(obj)


def export(annotation_files: Generator[dt.AnnotationFile, None, None], output_dir: Path):
    output = build_json(list(annotation_files))
    # TODO, maybe an optional output name (like the dataset name if available)
    output_file_path = (output_dir / "output").with_suffix(".json")
    with open(output_file_path, "w") as f:
        json.dump(output, f, cls=NumpyEncoder, indent=1)


def build_json(annotation_files):
    categories = calculate_categories(annotation_files)
    tag_categories = calculate_tag_categories(annotation_files)
    return {
        "info": build_info(),
        "licenses": build_licenses(),
        "images": build_images(annotation_files, tag_categories),
        "annotations": list(build_annotations(annotation_files, categories)),
        "categories": list(build_categories(categories)),
        "tag_categories": list(build_tag_categories(tag_categories)),
    }


def calculate_categories(annotation_files: List[dt.AnnotationFile]):
    categories = {}
    for annotation_file in annotation_files:
        for annotation_class in annotation_file.annotation_classes:
            if annotation_class.name not in categories and annotation_class.annotation_type in [
                "polygon",
                "complex_polygon",
                "bounding_box",
            ]:
                categories[annotation_class.name] = len(categories)
    return categories


def calculate_tag_categories(annotation_files: List[dt.AnnotationFile]):
    categories = {}
    for annotation_file in annotation_files:
        for annotation_class in annotation_file.annotation_classes:
            if annotation_class.name not in categories and annotation_class.annotation_type == "tag":
                categories[annotation_class.name] = len(categories)
    return categories


def build_info():
    # TODO fill out these fields in a meaningful way
    today = date.today()
    return {
        "description": "Exported from Darwin",
        "url": "n/a",
        "version": "n/a",
        "year": today.year,
        "contributor": "n/a",
        "date_created": today.strftime("%Y/%m/%d"),
    }


def build_licenses():
    return [{"url": "n/a", "id": 0, "name": "placeholder license"}]


def build_images(annotation_files, tag_categories):
    return [
        build_image(annotation_file, tag_categories)
        for annotation_file in sorted(annotation_files, key=lambda x: x.seq)
    ]


def build_image(annotation_file, tag_categories):
    tags = [
        annotation for annotation in annotation_file.annotations if annotation.annotation_class.annotation_type == "tag"
    ]
    return {
        "license": 0,
        "file_name": annotation_file.filename,
        "coco_url": "n/a",
        "height": annotation_file.image_height,
        "width": annotation_file.image_width,
        "date_captured": "",
        "flickr_url": "n/a",
        "darwin_url": annotation_file.image_url,
        "darwin_workview_url": annotation_file.workview_url,
        "id": annotation_file.seq,
        "tag_ids": [tag_categories[tag.annotation_class.name] for tag in tags],
    }


def build_annotations(annotation_files, categories):
    annotation_id = 0
    for annotation_file in annotation_files:
        for annotation in annotation_file.annotations:
            annotation_id += 1
            annotation_data = build_annotation(annotation_file, annotation_id, annotation, categories)
            if annotation_data:
                yield annotation_data


def build_annotation(annotation_file, annotation_id, annotation: dt.Annotation, categories):
    annotation_type = annotation.annotation_class.annotation_type
    if annotation_type == "polygon":
        sequences = convert_polygons_to_sequences(annotation.data["path"])
        x_coords = [s[0::2] for s in sequences]
        y_coords = [s[1::2] for s in sequences]
        min_x = np.min([np.min(x_coord) for x_coord in x_coords])
        min_y = np.min([np.min(y_coord) for y_coord in y_coords])
        max_x = np.max([np.max(x_coord) for x_coord in x_coords])
        max_y = np.max([np.max(y_coord) for y_coord in y_coords])
        w = max_x - min_x + 1
        h = max_y - min_y + 1
        # Compute the area of the polygon
        poly_area = np.sum([polygon_area(x_coord, y_coord) for x_coord, y_coord in zip(x_coords, y_coords)])

        return {
            "id": annotation_id,
            "image_id": annotation_file.seq,
            "category_id": categories[annotation.annotation_class.name],
            "segmentation": sequences,
            "area": poly_area,
            "bbox": [min_x, min_y, w, h],
            "iscrowd": 0,
            "extra": build_extra(annotation),
        }
    elif annotation_type == "complex_polygon":
        mask = np.zeros((annotation_file.image_height, annotation_file.image_width))
        sequences = convert_polygons_to_sequences(annotation.data["paths"])
        draw_polygon(mask, sequences, 1)
        counts = rle_encoding(mask)

        x_coords = [s[0::2] for s in sequences]
        y_coords = [s[1::2] for s in sequences]
        min_x = np.min([np.min(x_coord) for x_coord in x_coords])
        min_y = np.min([np.min(y_coord) for y_coord in y_coords])
        max_x = np.max([np.max(x_coord) for x_coord in x_coords])
        max_y = np.max([np.max(y_coord) for y_coord in y_coords])
        w = max_x - min_x + 1
        h = max_y - min_y + 1

        return {
            "id": annotation_id,
            "image_id": annotation_file.seq,
            "category_id": categories[annotation.annotation_class.name],
            "segmentation": {"counts": counts, "size": [annotation_file.image_width, annotation_file.image_height]},
            "area": 0,
            "bbox": [min_x, min_y, w, h],
            "iscrowd": 1,
            "extra": build_extra(annotation),
        }
    elif annotation_type == "tag":
        pass
    elif annotation_type == "bounding_box":
        x = annotation.data["x"]
        y = annotation.data["y"]
        w = annotation.data["w"]
        h = annotation.data["h"]
        return build_annotation(
            annotation_file,
            annotation_id,
            dt.make_polygon(
                annotation.annotation_class.name,
                [{"x": x, "y": y}, {"x": x + w, "y": y}, {"x": x + w, "y": y + h}, {"x": x, "y": y + h}],
            ),
            categories,
        )
    else:
        print(f"skipping unsupported annotation_type '{annotation_type}'")


def build_extra(annotation):
    data = {}
    instance_id_sub = annotation.get_sub("instance_id")
    attributes_sub = annotation.get_sub("attributes")
    text_sub = annotation.get_sub("text")

    if instance_id_sub:
        data["instance_id"] = instance_id_sub.data
    if attributes_sub:
        data["attributes"] = attributes_sub.data
    if text_sub:
        data["text"] = text_sub.data
    return data


def build_categories(categories):
    for name, id in categories.items():
        yield {"id": id, "name": name, "supercategory": "root"}


def build_tag_categories(categories):
    for name, id in categories.items():
        yield {"id": id, "name": name}


def polygon_area(x: np.ndarray, y: np.ndarray) -> float:
    """
    Returns the area of the input polygon, represented with two numpy arrays
    for x and y coordinates.
    """
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def rle_encoding(binary_mask):
    counts = []

    last_elem = 0
    running_length = 0
    for i, elem in enumerate(binary_mask.ravel(order="F")):
        if elem != last_elem:
            counts.append(running_length)
            running_length = 0
            last_elem = elem
        running_length += 1

    counts.append(running_length)
    return counts
