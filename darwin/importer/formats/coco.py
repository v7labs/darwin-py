from logging import getLogger
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple
from uuid import uuid4

import numpy as np
import orjson as json
from upolygon import find_contours, rle_decode

import darwin.datatypes as dt
from darwin.path_utils import deconstruct_full_path
from darwin.utils import attempt_decode

DEPRECATION_MESSAGE = """

This function is going to be turned into private. This means that breaking 
changes in its interface and implementation are to be expected. We encourage using ``parse_annotation`` 
instead of calling this low-level function directly.
"""


logger = getLogger(__name__)


def parse_path(path: Path) -> Optional[List[dt.AnnotationFile]]:
    """
    Parses the given ``coco`` file and returns a ``List[dt.AnnotationFile]`` with the parsed
    information.

    Parameters
    ----------
    path : Path
        The ``Path`` to the ``coco`` file.

    Returns
    -------
    Optional[List[dt.AnnotationFile]]
        Returns ``None`` if the given file is not in ``json`` format, or ``List[dt.AnnotationFile]``
        otherwise.
    """
    if path.suffix != ".json":
        return None
    data = attempt_decode(path)
    return list(parse_json(path, data))


def parse_json(
    path: Path,
    data: Dict[str, dt.UnknownType],
    rle_as_masks: bool = False,
) -> Iterator[dt.AnnotationFile]:
    """
    Parses the given ``json`` structure into an ``Iterator[dt.AnnotationFile]``.

    Parameters
    ----------
    path : Path
        The ``Path`` where file containing the ``data`` is.
    data : Dict[str, Any]
        The ``json`` data to process.
    rle_as_masks : bool, default: False
        If ``True``, RLE segmentations are imported as Darwin raster ``mask``
        annotations (plus one ``raster_layer`` per image) instead of being
        converted to polygons.

    Returns
    -------
    Iterator[dt.AnnotationFile]
        An iterator of all parsed annotation files.
    """
    annotations = data["annotations"]
    image_lookup_table = {image["id"]: image for image in data["images"]}
    category_lookup_table = {
        category["id"]: category for category in data["categories"]
    }
    tag_categories = data.get("tag_categories") or []
    tag_category_lookup_table = {
        category["id"]: category for category in tag_categories
    }
    image_annotations: Dict[str, dt.UnknownType] = {}
    image_rle_annotations: Dict[str, List[Dict[str, dt.UnknownType]]] = {}

    for image in data["images"]:
        image_id = image["id"]
        tag_ids = image.get("tag_ids") or []

        if image_id not in image_annotations:
            image_annotations[image_id] = []

        for tag_id in tag_ids:
            tag = tag_category_lookup_table[tag_id]
            image_annotations[image_id].append(dt.make_tag(tag["name"]))

    for annotation in annotations:
        image_id = annotation["image_id"]
        annotation["category_id"]
        annotation["segmentation"]
        if image_id not in image_annotations:
            image_annotations[image_id] = []
        if (
            rle_as_masks
            and isinstance(annotation["segmentation"], dict)
            and "counts" in annotation["segmentation"]
        ):
            image_rle_annotations.setdefault(image_id, []).append(annotation)
        else:
            image_annotations[image_id].extend(
                parse_annotation(annotation, category_lookup_table)
            )

    for image_id, rle_annotations in image_rle_annotations.items():
        image = image_lookup_table[int(image_id)]
        image_annotations[image_id].extend(
            _build_mask_annotations(
                rle_annotations,
                category_lookup_table,
                image_height=image.get("height"),
                image_width=image.get("width"),
            )
        )

    for image_id in image_annotations.keys():
        image = image_lookup_table[int(image_id)]
        annotations = list(filter(None, image_annotations[image_id]))
        annotation_classes = {annotation.annotation_class for annotation in annotations}
        remote_path, filename = deconstruct_full_path(image["file_name"])
        yield dt.AnnotationFile(
            path, filename, annotation_classes, annotations, remote_path=remote_path
        )


def parse_annotation(
    annotation: Dict[str, dt.UnknownType],
    category_lookup_table: Dict[str, dt.UnknownType],
) -> List[dt.Annotation]:
    """
    Parses the given ``json`` dictionary into a darwin ``Annotation`` if possible.

    Parameters
    ----------
    annotation : Dict[str, dt.UnknownType]
        The ``json`` dictionary to parse.
    category_lookup_table : Dict[str, dt.UnknownType]
        Dictionary with all the categories from the ``coco`` file.

    Returns
    -------
    Optional[dt.Annotation]
        A darwin ``Annotation`` if the parse was successful, or ``None`` otherwise.
    """
    category = category_lookup_table[annotation["category_id"]]
    segmentation = annotation["segmentation"]
    iscrowd = annotation.get("iscrowd") == 1

    if iscrowd:
        logger.warn(
            f"Skipping annotation {annotation.get('id')} because it is a crowd "
            "annotation, and Darwin does not support import of COCO crowd annotations."
        )
        return []

    if len(segmentation) == 0 and len(annotation["bbox"]) == 4:
        x, y, w, h = map(int, annotation["bbox"])
        return [dt.make_bounding_box(category["name"], x, y, w, h)]
    elif (
        len(segmentation) == 0
        and len(annotation["bbox"]) == 1
        and len(annotation["bbox"][0]) == 4
    ):
        x, y, w, h = map(int, annotation["bbox"][0])
        return [dt.make_bounding_box(category["name"], x, y, w, h)]
    elif isinstance(segmentation, dict):
        logger.warn(
            "warning, converting complex coco rle mask to polygon, could take some time"
        )
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
        return [dt.make_polygon(category["name"], paths)]
    elif isinstance(segmentation, list):
        paths = segmentation if isinstance(segmentation[0], list) else [segmentation]
        point_paths = []
        for path in paths:
            point_path = []
            points = iter(path)
            while True:
                try:
                    x, y = next(points), next(points)
                    point_path.append({"x": x, "y": y})
                except StopIteration:
                    break
            point_paths.append(point_path)
        return [dt.make_polygon(category["name"], point_paths)]
    else:
        return []


def _encode_dense_rle(label_map: "np.ndarray") -> List[int]:
    """Encodes a 2D label map into Darwin's row-major [value, count, ...] dense RLE."""
    flat = label_map.flatten()
    boundaries = np.flatnonzero(flat[1:] != flat[:-1]) + 1
    starts = np.concatenate(([0], boundaries))
    lengths = np.diff(np.concatenate((starts, [flat.size])))
    dense_rle: List[int] = []
    for value, length in zip(flat[starts], lengths):
        dense_rle.extend((int(value), int(length)))
    return dense_rle


def _build_mask_annotations(
    rle_annotations: List[Dict[str, dt.UnknownType]],
    category_lookup_table: Dict[str, dt.UnknownType],
    image_height: Optional[int] = None,
    image_width: Optional[int] = None,
) -> List[dt.Annotation]:
    """
    Converts one image's COCO RLE annotations into Darwin ``mask`` annotations
    plus a single ``raster_layer`` annotation.

    Overlaps are resolved by annotation order: later annotations paint over
    earlier ones. Masks left without any visible pixel are dropped.

    When ``image_height``/``image_width`` are both provided (the COCO image
    record's authoritative dimensions), they set the canvas up front, and
    every RLE's own ``segmentation["size"]`` is validated against them. This
    prevents a malformed leading RLE (e.g. with the wrong ``size``) from
    silently setting the wrong canvas and causing later, valid RLEs to be
    skipped as "mismatched". When either dimension is ``None``, the first
    RLE's ``size`` is used as the canvas, preserving prior behavior for
    direct callers that don't pass image dimensions.
    """
    height: Optional[int] = image_height
    width: Optional[int] = image_width
    label_map: Optional[np.ndarray] = None
    if height is not None and width is not None:
        label_map = np.zeros((height, width), dtype=np.int32)
    painted_masks: List[Tuple[dt.Annotation, int]] = []
    next_label = 1

    for annotation in rle_annotations:
        try:
            segmentation = annotation["segmentation"]
            seg_height, seg_width = segmentation["size"]
            if height is None or width is None or label_map is None:
                height, width = seg_height, seg_width
                label_map = np.zeros((height, width), dtype=np.int32)
            elif (seg_height, seg_width) != (height, width):
                logger.warning(
                    f"Skipping RLE annotation {annotation.get('id')}: size "
                    f"{segmentation['size']} does not match image size [{height}, {width}]"
                )
                continue
            counts = segmentation["counts"]
            if not isinstance(counts, list):
                counts = decode_binary_rle(counts)
            if sum(counts) != height * width:
                logger.warning(
                    f"Skipping RLE annotation {annotation.get('id')}: counts cover "
                    f"{sum(counts)} pixels, expected {height * width}"
                )
                continue
            binary = np.array(rle_decode(counts, [width, height])).reshape(
                height, width
            )
            category = category_lookup_table[annotation["category_id"]]
            mask = dt.make_mask(category["name"])
            mask.id = str(uuid4())
            label_map[binary > 0] = next_label
            painted_masks.append((mask, next_label))
            next_label += 1
        except Exception as e:
            logger.warning(f"Skipping RLE annotation {annotation.get('id')}: {e}")
            continue

    if label_map is None:
        return []

    visible_labels = set(np.unique(label_map))
    mask_annotation_ids_mapping: Dict[str, int] = {}
    visible_masks: List[dt.Annotation] = []
    for mask, label in painted_masks:
        if label not in visible_labels:
            logger.warning(
                f"Skipping mask '{mask.annotation_class.name}': fully occluded by "
                "later annotations"
            )
            continue
        mask_annotation_ids_mapping[mask.id] = label
        visible_masks.append(mask)

    if not visible_masks:
        return []

    raster_layer = dt.make_raster_layer(
        "__raster_layer__",
        mask_annotation_ids_mapping,
        int(height * width),
        _encode_dense_rle(label_map),
    )
    raster_layer.id = str(uuid4())
    return visible_masks + [raster_layer]


def _decode_file(current_encoding: str, path: Path):
    if current_encoding == "system_default":
        with path.open() as f:
            data = json.loads(f.read())
    else:
        with path.open(encoding=current_encoding) as f:
            data = json.loads(f.read())
    return list(parse_json(path, data))


def decode_binary_rle(data: str) -> List[int]:
    """
    Decodes binary rle to integer list rle.
    """
    m = len(data)
    counts = [0] * m
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
            x += counts[h - 2]
        counts[h] = x
        h += 1
    return counts[0:h]
