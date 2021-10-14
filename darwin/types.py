from typing import Dict, List, Tuple, Callable, Iterator, Union, Any
from darwin.datatypes import AnnotationFile
from pathlib import Path


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
