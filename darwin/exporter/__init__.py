from importlib import import_module

from darwin.datatypes import ExportParser

from .exporter import export_annotations  # noqa


class ExporterNotFoundError(ModuleNotFoundError):
    pass


def get_exporter(format: str) -> ExportParser:
    try:
        module = import_module(f"darwin.exporter.formats.{format}")
        return getattr(module, "export")
    except ModuleNotFoundError:
        raise ExporterNotFoundError
