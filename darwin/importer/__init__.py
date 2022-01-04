from importlib import import_module
from types import ModuleType

from .importer import import_annotations  # noqa


class ImporterNotFoundError(ModuleNotFoundError):
    pass


def get_importer(format: str) -> ModuleType:
    try:
        return import_module(f"darwin.exporter.formats.{format}")
    except ModuleNotFoundError:
        raise ImporterNotFoundError
