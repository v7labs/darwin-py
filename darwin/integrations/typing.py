from typing import Dict, List, NewType, TypedDict

from darwin.datatypes import Annotation


class LoadParams(TypedDict):
    classes: List[str]


class InferParams(TypedDict):
    pass


InferResult = List[Annotation]


class TrainParams(TypedDict):
    pass

TrainResult = Dict

