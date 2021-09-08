from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from .train_handler import TrainHandler
from .typing import InferParams, LoadParams, TrainParams


class IntegrationStrategy(ABC):
    @abstractmethod
    def load(self, checkpoint_path: Path, params: LoadParams) -> None:
        raise NotImplementedError()

    @abstractmethod
    def infer(self, file_paths: List[Path], params: InferParams) -> None:
        raise NotImplementedError()

    @abstractmethod
    def train(self, train_handler: TrainHandler, params: TrainParams) -> None:
        raise NotImplementedError()
