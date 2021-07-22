import json
from pathlib import Path
from typing import List, Optional

from upolygon import find_contours, rle_decode

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
        yield dt.AnnotationFile(path, image["file_name"], annotation_classes, annotations, remote_path="/")


def parse_annotation(annotation, category_lookup_table):
    category = category_lookup_table[annotation["category_id"]]
    segmentation = annotation["segmentation"]
    iscrowd = annotation.get("iscrowd") == 1

    if iscrowd:
        print("Warning, unsupported RLE, skipping")
        return None

    if len(segmentation) == 0 and len(annotation["bbox"]) == 4:
        x, y, w, h = map(int, annotation["bbox"])
        return dt.make_bounding_box(category["name"], x, y, w, h)
    elif len(segmentation) == 0 and len(annotation["bbox"]) == 1 and len(annotation["bbox"][0]) == 4:
        x, y, w, h = map(int, annotation["bbox"][0])
        return dt.make_bounding_box(category["name"], x, y, w, h)
    elif isinstance(segmentation, dict):
        print("warning, converting complex coco rle mask to polygon, could take some time")
        if isinstance(segmentation["counts"], list):
            mask = rle_decode(segmentation["counts"], segmentation["size"][::-1])
        else:
            counts = decode_binary_rle(segmentation["counts"])
            mask = rle_decode(counts, segmentation["size"][::-1])

        _labels, external, _internal = find_contours(mask)
        paths = []
        for external_path in external:
            # skip paths with less than 2 points
            if len(external_path) // 2 <= 2:
                continue
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
    elif isinstance(segmentation, list):
        path = []
        points = iter(segmentation[0] if isinstance(segmentation[0], list) else segmentation)
        while True:
            try:
                x, y = next(points), next(points)
                path.append({"x": x, "y": y})
            except StopIteration:
                break
        return dt.make_polygon(category["name"], path)
    else:
        return None


def decode_binary_rle(data):
    """
    decodes binary rle to integer list rle
    """
    m = len(data)
    cnts = [0] * m
    h = 0
    p = 0
    while p < m:
        x = 0
        k = 0
        more = 1
        while more > 0:
            c = ord(data[p]) - 48
            x |= (c & 0x1F) << 5 * k
            more = c & 0x20
            p = p + 1
            k = k + 1
            if more == 0 and (c & 0x10) != 0:
                x |= -1 << 5 * k
        if h > 2:
            x += cnts[h - 2]
        cnts[h] = x
        h += 1
    return cnts[0:h]
