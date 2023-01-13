from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from zlib import crc32

import deprecation
import numpy as np
import orjson as json
from upolygon import draw_polygon, rle_encode

import darwin.datatypes as dt
from darwin.exporter.formats.numpy_encoder import NumpyEncoder
from darwin.utils import convert_polygons_to_sequences
from darwin.version import __version__

DEPRECATION_MESSAGE = """

This function is going to be turned into private. This means that breaking 
changes in its interface and implementation are to be expected. We encourage using ``export`` 
instead of calling this low-level function directly.

"""


def export(annotation_files: Iterator[dt.AnnotationFile], output_dir: Path) -> None:
    """
    Exports the given ``AnnotationFile``\\s into the coco format inside of the given ``output_dir``.

    Parameters
    ----------
    annotation_files : Iterator[dt.AnnotationFile]
        The ``AnnotationFile``\\s to be exported.
    output_dir : Path
        The folder where the new coco file will be.
    """
    output = _build_json(list(annotation_files))
    output_file_path = (output_dir / "output").with_suffix(".json")
    with open(output_file_path, "w") as f:
        op = json.dumps(output, option=json.OPT_INDENT_2 | json.OPT_SERIALIZE_NUMPY).decode("utf-8")
        f.write(op)


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_json(annotation_files: List[dt.AnnotationFile]) -> Dict[str, Any]:
    categories: Dict[str, int] = calculate_categories(annotation_files)
    tag_categories: Dict[str, int] = calculate_tag_categories(annotation_files)
    return {
        "info": build_info(),
        "licenses": build_licenses(),
        "images": build_images(annotation_files, tag_categories),
        "annotations": list(build_annotations(annotation_files, categories)),
        "categories": list(build_categories(categories)),
        "tag_categories": list(build_tag_categories(tag_categories)),
    }


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def calculate_categories(annotation_files: List[dt.AnnotationFile]) -> Dict[str, int]:
    categories: Dict[str, int] = {}
    for annotation_file in annotation_files:
        for annotation_class in annotation_file.annotation_classes:
            if annotation_class.name not in categories and annotation_class.annotation_type in [
                "polygon",
                "complex_polygon",
                "bounding_box",
            ]:
                categories[annotation_class.name] = _calculate_category_id(annotation_class)
    return categories


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def calculate_tag_categories(annotation_files: List[dt.AnnotationFile]) -> Dict[str, int]:
    categories: Dict[str, int] = {}
    for annotation_file in annotation_files:
        for annotation_class in annotation_file.annotation_classes:
            if annotation_class.name not in categories and annotation_class.annotation_type == "tag":
                categories[annotation_class.name] = _calculate_category_id(annotation_class)
    return categories


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_info() -> Dict[str, Any]:
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


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_licenses() -> List[Dict[str, Any]]:
    return [{"url": "n/a", "id": 0, "name": "placeholder license"}]


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_images(annotation_files: List[dt.AnnotationFile], tag_categories: Dict[str, int]) -> List[Dict[str, Any]]:
    return [
        build_image(annotation_file, tag_categories)
        for annotation_file in sorted(annotation_files, key=lambda x: x.seq)
    ]


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_image(annotation_file: dt.AnnotationFile, tag_categories: Dict[str, int]) -> Dict[str, Any]:
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
        "id": _build_image_id(annotation_file),
        "tag_ids": [tag_categories[tag.annotation_class.name] for tag in tags],
    }


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_annotations(
    annotation_files: List[dt.AnnotationFile], categories: Dict[str, int]
) -> Iterator[Optional[Dict[str, Any]]]:
    annotation_id = 0
    for annotation_file in annotation_files:
        for annotation in annotation_file.annotations:
            annotation_id += 1
            annotation_data = build_annotation(annotation_file, annotation_id, annotation, categories)
            if annotation_data:
                yield annotation_data


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_annotation(
    annotation_file: dt.AnnotationFile, annotation_id: int, annotation: dt.Annotation, categories: Dict[str, int]
) -> Optional[Dict[str, Any]]:
    annotation_type = annotation.annotation_class.annotation_type
    if annotation_type == "polygon":
        sequences = convert_polygons_to_sequences(annotation.data["path"], rounding=False)
        x_coords = [s[0::2] for s in sequences]
        y_coords = [s[1::2] for s in sequences]
        min_x = np.min([np.min(x_coord) for x_coord in x_coords])
        min_y = np.min([np.min(y_coord) for y_coord in y_coords])
        max_x = np.max([np.max(x_coord) for x_coord in x_coords])
        max_y = np.max([np.max(y_coord) for y_coord in y_coords])
        w = max_x - min_x
        h = max_y - min_y
        # Compute the area of the polygon
        poly_area = np.sum([polygon_area(x_coord, y_coord) for x_coord, y_coord in zip(x_coords, y_coords)])

        return {
            "id": annotation_id,
            "image_id": _build_image_id(annotation_file),
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
        counts = rle_encode(mask)

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
            "image_id": _build_image_id(annotation_file),
            "category_id": categories[annotation.annotation_class.name],
            "segmentation": {"counts": counts, "size": [annotation_file.image_height, annotation_file.image_width]},
            "area": np.sum(mask),
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
                None,
                annotation.subs,
            ),
            categories,
        )
    else:
        print(f"skipping unsupported annotation_type '{annotation_type}'")


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_extra(annotation: dt.Annotation) -> Dict[str, Any]:
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


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_categories(categories: Dict[str, int]) -> Iterator[Dict[str, Any]]:
    for name, id in categories.items():
        yield {"id": id, "name": name, "supercategory": "root"}


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_tag_categories(categories: Dict[str, int]) -> Iterator[Dict[str, Any]]:
    for name, id in categories.items():
        yield {"id": id, "name": name}


@deprecation.deprecated(
    deprecated_in="0.7.7",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def polygon_area(x: np.ndarray, y: np.ndarray) -> float:
    """
    Returns the area of the input polygon, represented with two numpy arrays
    for x and y coordinates.
    """
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def _build_json(annotation_files: List[dt.AnnotationFile]) -> Dict[str, Any]:
    categories: Dict[str, int] = _calculate_categories(annotation_files)
    tag_categories: Dict[str, int] = _calculate_tag_categories(annotation_files)
    return {
        "info": _build_info(),
        "licenses": _build_licenses(),
        "images": _build_images(annotation_files, tag_categories),
        "annotations": list(_build_annotations(annotation_files, categories)),
        "categories": list(_build_categories(categories)),
        "tag_categories": list(_build_tag_categories(tag_categories)),
    }


def _calculate_categories(annotation_files: List[dt.AnnotationFile]) -> Dict[str, int]:
    categories: Dict[str, int] = {}
    for annotation_file in annotation_files:
        for annotation_class in annotation_file.annotation_classes:
            if annotation_class.name not in categories and annotation_class.annotation_type in [
                "polygon",
                "complex_polygon",
                "bounding_box",
            ]:
                categories[annotation_class.name] = _calculate_category_id(annotation_class)
    return categories


def _calculate_tag_categories(annotation_files: List[dt.AnnotationFile]) -> Dict[str, int]:
    categories: Dict[str, int] = {}
    for annotation_file in annotation_files:
        for annotation_class in annotation_file.annotation_classes:
            if annotation_class.name not in categories and annotation_class.annotation_type == "tag":
                categories[annotation_class.name] = _calculate_category_id(annotation_class)
    return categories


def _calculate_category_id(annotation_class: dt.AnnotationClass) -> int:
    return crc32(str.encode(annotation_class.name))


def _build_info() -> Dict[str, Any]:
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


def _build_licenses() -> List[Dict[str, Any]]:
    return [{"url": "n/a", "id": 0, "name": "placeholder license"}]


def _build_images(annotation_files: List[dt.AnnotationFile], tag_categories: Dict[str, int]) -> List[Dict[str, Any]]:
    return [
        _build_image(annotation_file, tag_categories)
        for annotation_file in sorted(annotation_files, key=lambda x: x.seq)
    ]


def _build_image(annotation_file: dt.AnnotationFile, tag_categories: Dict[str, int]) -> Dict[str, Any]:
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
        "id": _build_image_id(annotation_file),
        "tag_ids": [tag_categories[tag.annotation_class.name] for tag in tags],
    }


def _build_image_id(annotation_file: dt.AnnotationFile) -> int:
    # CoCo file format requires unique image IDs
    # darwin 1.0 produces unique 'seq' values that can be used
    # darwin 2.0 does not provide `seq` so we hash the path + filename to produce a unique-enough 32bit int
    if annotation_file.seq:
        return annotation_file.seq
    else:
        full_path = str(Path(annotation_file.remote_path or "/") / Path(annotation_file.filename))
        return crc32(str.encode(full_path))


def _build_annotations(
    annotation_files: List[dt.AnnotationFile], categories: Dict[str, int]
) -> Iterator[Optional[Dict[str, Any]]]:
    annotation_id = 0
    for annotation_file in annotation_files:
        for annotation in annotation_file.annotations:
            annotation_id += 1
            annotation_data = _build_annotation(annotation_file, annotation_id, annotation, categories)
            if annotation_data:
                yield annotation_data


def _build_annotation(
    annotation_file: dt.AnnotationFile, annotation_id: int, annotation: dt.Annotation, categories: Dict[str, int]
) -> Optional[Dict[str, Any]]:
    annotation_type = annotation.annotation_class.annotation_type
    if annotation_type == "polygon":
        sequences = convert_polygons_to_sequences(annotation.data["path"], rounding=False)
        x_coords = [s[0::2] for s in sequences]
        y_coords = [s[1::2] for s in sequences]
        min_x = np.min([np.min(x_coord) for x_coord in x_coords])
        min_y = np.min([np.min(y_coord) for y_coord in y_coords])
        max_x = np.max([np.max(x_coord) for x_coord in x_coords])
        max_y = np.max([np.max(y_coord) for y_coord in y_coords])
        w = max_x - min_x
        h = max_y - min_y
        # Compute the area of the polygon
        poly_area = np.sum([_polygon_area(x_coord, y_coord) for x_coord, y_coord in zip(x_coords, y_coords)])

        return {
            "id": annotation_id,
            "image_id": _build_image_id(annotation_file),
            "category_id": categories[annotation.annotation_class.name],
            "segmentation": sequences,
            "area": poly_area,
            "bbox": [min_x, min_y, w, h],
            "iscrowd": 0,
            "extra": _build_extra(annotation),
        }
    elif annotation_type == "complex_polygon":
        mask = np.zeros((annotation_file.image_height, annotation_file.image_width))
        sequences = convert_polygons_to_sequences(annotation.data["paths"])
        draw_polygon(mask, sequences, 1)
        counts = rle_encode(mask)

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
            "image_id": _build_image_id(annotation_file),
            "category_id": categories[annotation.annotation_class.name],
            "segmentation": {"counts": counts, "size": [annotation_file.image_height, annotation_file.image_width]},
            "area": np.sum(mask),
            "bbox": [min_x, min_y, w, h],
            "iscrowd": 1,
            "extra": _build_extra(annotation),
        }
    elif annotation_type == "tag":
        pass
    elif annotation_type == "bounding_box":
        x = annotation.data["x"]
        y = annotation.data["y"]
        w = annotation.data["w"]
        h = annotation.data["h"]

        return _build_annotation(
            annotation_file,
            annotation_id,
            dt.make_polygon(
                annotation.annotation_class.name,
                [{"x": x, "y": y}, {"x": x + w, "y": y}, {"x": x + w, "y": y + h}, {"x": x, "y": y + h}],
                None,
                annotation.subs,
            ),
            categories,
        )
    else:
        print(f"skipping unsupported annotation_type '{annotation_type}'")


def _build_extra(annotation: dt.Annotation) -> Dict[str, Any]:
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


def _build_categories(categories: Dict[str, int]) -> Iterator[Dict[str, Any]]:
    for name, id in categories.items():
        yield {"id": id, "name": name, "supercategory": "root"}


def _build_tag_categories(categories: Dict[str, int]) -> Iterator[Dict[str, Any]]:
    for name, id in categories.items():
        yield {"id": id, "name": name}


def _polygon_area(x: np.ndarray, y: np.ndarray) -> float:
    """
    Returns the area of the input polygon, represented with two numpy arrays
    for x and y coordinates.
    """
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
