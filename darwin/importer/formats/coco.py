import json
from pathlib import Path
from typing import List, Optional

import numpy as np
from upolygon import find_contours

import darwin.datatypes as dt


def parse_file(path: Path) -> Optional[List[dt.AnnotationFile]]:
    if path.suffix != ".json":
        return

    with path.open() as f:
        data = json.load(f)
        return list(parse_json(path, data))


def parse_json(path, data):
    annotations = data["annotations"]
    image_lookup_table = {image["id"]: image for image in data["images"]}
    category_lookup_table = {category["id"]: category for category in data["categories"]}
    image_annotations = {}

    for annotation in annotations:
        image_id = annotation["image_id"]
        annotation["category_id"]
        annotation["segmentation"]
        if image_id not in image_annotations:
            image_annotations[image_id] = []
        image_annotations[image_id].append(parse_annotation(annotation, category_lookup_table))

    for image_id in image_annotations.keys():
        image = image_lookup_table[image_id]
        annotations = list(filter(None, image_annotations[image_id]))
        annotation_classes = set([annotation.annotation_class for annotation in annotations])
        yield dt.AnnotationFile(path, image["file_name"], annotation_classes, annotations)


def parse_annotation(annotation, category_lookup_table):
    category = category_lookup_table[annotation["category_id"]]
    segmentation = annotation["segmentation"]
    iscrowd = annotation.get("iscrowd") == 1

    if iscrowd:
        print("Warning, unsupported RLE, skipping")
        return None

    if len(segmentation) > 1:
        print("warning, converting complex coco rle mask to polygon, could take some time")
        mask = rle_decoding(segmentation["counts"], segmentation["size"])
        _labels, external, _internal = find_contours(mask)
        paths = []
        for external_path in external:
            path = []
            points = iter(external_path)
            while True:
                try:
                    x, y = next(points), next(points)
                    path.append({"x": x, "y": y})
                except StopIteration:
                    break
            paths.append(path)
        return dt.make_complex_polygon(category["name"], paths)
    path = []
    points = iter(segmentation[0])
    while True:
        try:
            x, y = next(points), next(points)
            path.append({"x": x, "y": y})
        except StopIteration:
            break
    return dt.make_polygon(category["name"], path)


def rle_decoding(counts, shape):
    img = np.zeros(shape[0] * shape[1], dtype=np.uint8)
    val = 1
    n = 0
    for pos in range(len(counts)):
        val = not val
        img[n : n + counts[pos]] = val
        n += counts[pos]
    return img.reshape(shape)
