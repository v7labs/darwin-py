from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Tuple, Union

from rich.console import Console
from rich.theme import Theme

from darwin.datatypes import (
    Annotation,
    AnnotationFile,
    ConversionError,
    VideoAnnotation,
    YoloAnnotation,
)


def export(annotation_files: Iterable[AnnotationFile], output_dir: Path) -> None:
    """
    Exports the given ``AnnotationFile``s into the yolo format inside of the given ``output_dir``.

    Parameters
    ----------
    annotation_files : Iterator[dt.AnnotationFile]
        The ``AnnotationFile``s to be exported.
    output_dir : Path
        The folder where the new coco file will be.
    """
    console = Console(theme=_console_theme())

    output_dir.mkdir(parents=True, exist_ok=True)
    for annotation_file in annotation_files:
        output_file_path = (output_dir / annotation_file.filename).with_suffix(".txt")
        errors, yolo_annotations = _convert_file(annotation_file)

        with open(output_file_path, "w") as f:
            for yolo in yolo_annotations:
                f.write(f"{yolo.annotation_class} {yolo.x} {yolo.y} {yolo.width} {yolo.height}")

        for err in errors:
            console.print(
                f"Failed to convert: '{err.filename}'. Reason: {err.reason}. Annotation: {err.annotation}\n",
                style="error",
            )


def _convert_file(file: AnnotationFile) -> Tuple[List[ConversionError], List[YoloAnnotation]]:
    conversions: List[Union[ConversionError, YoloAnnotation]] = _to_yolo(file)
    yolo_annotations: List[YoloAnnotation] = [x for x in conversions if isinstance(x, YoloAnnotation)]
    errors: List[ConversionError] = [x for x in conversions if isinstance(x, ConversionError)]
    return (errors, yolo_annotations)


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


def _console_theme() -> Theme:
    return Theme({"success": "bold green", "warning": "bold yellow", "error": "bold red"})
