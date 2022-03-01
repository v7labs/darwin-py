from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

from rich.console import Console

from darwin.console_settings import console_theme
from darwin.datatypes import (
    Annotation,
    AnnotationFile,
    ConversionError,
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
    """

    annotation_class: str
    x: float
    y: float
    width: float
    height: float

    def __str__(self) -> str:
        return f"{self.annotation_class} {self.x} {self.y} {self.width} {self.height}"


def export(annotation_files: Iterable[AnnotationFile], output_dir: Path, console: Optional[Console] = None) -> None:
    """
    Exports the given ``AnnotationFile``s into the yolo format inside of the given ``output_dir``.

    Each output file created will have a ``__str__`` representation of a ``YoloAnnotation`` for each
    annotation that was successfully converted into a YOLO bounding box.

    Parameters
    ----------
    annotation_files : Iterator[dt.AnnotationFile]
        The ``AnnotationFile``s to be exported.
    output_dir : Path
        The folder where the new coco file will be.
    """
    printer: Optional[Console] = console
    if printer is None:
        printer = Console(theme=console_theme())

    output_dir.mkdir(parents=True, exist_ok=True)
    for annotation_file in annotation_files:
        output_file_path = (output_dir / annotation_file.filename).with_suffix(".txt")
        errors, yolo_annotations = _convert_file(annotation_file)

        with open(output_file_path, "w") as f:
            for yolo in yolo_annotations:
                f.write(str(yolo))

        for err in errors:
            printer.print(
                f"Failed to convert: '{err.filename}'. Reason: {err.reason}. Annotation: {err.annotation}\n",
                style="error",
            )


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

    annotation_type: str = annotation.annotation_class.annotation_type
    if annotation_type == "bounding_box":
        return _from_bounding_box(annotation)

    return ConversionError(
        reason=f"Unsupported annotation type: {annotation_type}",
        annotation=annotation,
        filename=annotation_file.path,
    )


def _from_bounding_box(annotation: Annotation) -> YoloAnnotation:
    name: str = annotation.annotation_class.name
    bbox: Dict[str, float] = annotation.data.get("bounding_box", {})
    return YoloAnnotation(annotation_class=name, x=bbox["x"], y=bbox["y"], width=bbox["w"], height=bbox["h"])


def _map_list(fun: Callable[[Any], Any], the_list: List[Any]) -> List[Any]:
    return list(map(fun, the_list))
