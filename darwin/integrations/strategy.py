from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from .train_handler import TrainHandler
from .typing import InferParams, InferResult, LoadParams, TrainParams, TrainResult


class IntegrationStrategy(ABC):
    @abstractmethod
    def load(self, weights_path: Optional[Path], params: LoadParams) -> None:
        pass

    @abstractmethod
    def infer(self, file_paths: List[Path], params: InferParams) -> InferResult:
        pass

    @abstractmethod
    def train(self, train_handler: TrainHandler, params: TrainParams) -> TrainResult:
        pass
