from importlib import import_module
from types import ModuleType

from .exporter import export_annotations  # noqa


class ExporterNotFoundError(ModuleNotFoundError):
    pass


def get_exporter(format: str) -> ModuleType:
    try:
        return import_module(f"darwin.exporter.formats.{format}")
    except ModuleNotFoundError:
        raise ExporterNotFoundError
