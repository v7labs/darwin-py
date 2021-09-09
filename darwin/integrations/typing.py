from dataclasses import dataclass
from typing import Dict, List

from darwin.datatypes import Annotation


@dataclass(frozen=True, eq=True)
class LoadParams:
    classes: List[str]


@dataclass(frozen=True, eq=True)
class InferParams:
    pass


InferResult = List[Annotation]


@dataclass(frozen=True, eq=True)
class TrainParams:
    pass


TrainResult = Dict

