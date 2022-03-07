from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Tuple, Union

from darwin.datatypes import (
    Annotation,
    AnnotationFile,
    ConversionError,
    ConversionResult,
    VideoAnnotation,
)


@dataclass(frozen=True, eq=True)
class YoloAnnotation:
    """
    Represents a YOLO annotation ready to be persisted as a bounding box.
    The XY coordinates represent the top left corner of said bounding box.

    The ``__str__`` representation of ``YoloAnnotation`` instances obeys the YOLO txt formatting,
    wherein each line will have the following content:

    .. code-block:: python
            annotation_name x y width height

    Attributes
    ----------
    annotation_class : str
        The name of the ``AnnotationClass``.
    x : float
        Left X coordinate of the bounding box.
    y : float
        Top Y coordinate of the bounding box.
    width : float
        Width of the bounding box.
    height : float
        Height of the bounding box.
    file : Path
        The path of the file that will contain this annotation.
    """

    annotation_class: str
    x: float
    y: float
    width: float
    height: float
    file: Path

    def __str__(self) -> str:
        return f"{self.annotation_class} {self.x} {self.y} {self.width} {self.height}"


def export(annotation_files: Iterable[AnnotationFile]) -> ConversionResult[YoloAnnotation]:
    """
    Attempty to convert the given ``AnnotationFile``s into the ``YoloAnnotation`` format.

    Successfull conversions will be under ``ConversionResult.conversions`` and will be represented
    by an instance of ``YoloAnnotation``, which has a ``__str__`` representation of an annotation
    that was successfully converted into a YOLO bounding box.

    Failed conversions will be under ``ConversionResult.errors`` and will be represented by an
    instance of ``ConversionError``, which has data regarding the failed conversion.

    Parameters
    ----------
    annotation_files : Iterable[AnnotationFile]
        The ``AnnotationFile``s to be converted.

    Returns
    -------
    ConversionResult[YoloAnnotation]
        An instance of ``ConversionResult``, containing all of the successful and failed conversions.
    """

    all_errors: List[ConversionError] = []
    all_conversions: List[YoloAnnotation] = []

    for file in annotation_files:
        errors, yolo_annotations = _convert_file(file)

        all_errors = all_errors + errors
        all_conversions = all_conversions + yolo_annotations

    return ConversionResult(errors=all_errors, conversions=all_conversions)


def _convert_file(file: AnnotationFile) -> Tuple[List[ConversionError], List[YoloAnnotation]]:
    conversions: List[Union[ConversionError, YoloAnnotation]] = _to_yolo(file)

    yolo_annotations: List[YoloAnnotation] = [x for x in conversions if isinstance(x, YoloAnnotation)]
    errors: List[ConversionError] = [x for x in conversions if isinstance(x, ConversionError)]

    return errors, yolo_annotations


def _to_yolo(annotation_file: AnnotationFile) -> List[Union[ConversionError, YoloAnnotation]]:
    create_yolo_annotation_with_file = partial(_create_yolo_annotation, annotation_file=annotation_file)
    return _map_list(create_yolo_annotation_with_file, annotation_file.annotations)


def _create_yolo_annotation(
    annotation: Union[VideoAnnotation, Annotation], annotation_file: AnnotationFile
) -> Union[ConversionError, YoloAnnotation]:
    if isinstance(annotation, VideoAnnotation):
        return ConversionError(
            reason="Cannot convert video annotations to yolo",
            annotation=annotation,
            filename=annotation_file.path,
        )

    export_file_path = Path(annotation_file.filename).with_suffix(".txt")

    annotation_type: str = annotation.annotation_class.annotation_type
    if annotation_type == "bounding_box":
        return _from_bounding_box(annotation, export_file_path)

    return ConversionError(
        reason=f"Unsupported annotation type: {annotation_type}",
        annotation=annotation,
        filename=annotation_file.path,
    )


def _from_bounding_box(annotation: Annotation, file: Path) -> YoloAnnotation:
    name: str = annotation.annotation_class.name
    bbox: Dict[str, float] = annotation.data
    return YoloAnnotation(annotation_class=name, x=bbox["x"], y=bbox["y"], width=bbox["w"], height=bbox["h"], file=file)


def _map_list(fun: Callable[[Any], Any], the_list: List[Any]) -> List[Any]:
    return list(map(fun, the_list))
