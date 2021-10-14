from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Tuple, Union

from darwin.datatypes import AnnotationFile

Point = Dict[str, float]
BoundingBox = Dict[str, float]
Polygon = List[Point]
ComplexPolygon = List[Polygon]

DarwinVersionNumber = Tuple[int, int, int]

ExportParser = Callable[[Iterator[AnnotationFile], Path], None]
ExporterFormat = Tuple[str, ExportParser]

ImportParser = Callable[[Path], Union[List[AnnotationFile], AnnotationFile, None]]
ImporterFormat = Tuple[str, ImportParser]

PathLike = Union[str, Path]
Team = Dict[str, Any]
