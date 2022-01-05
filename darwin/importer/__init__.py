from importlib import import_module

from darwin.datatypes import ImportParser

from .importer import import_annotations  # noqa


class ImporterNotFoundError(ModuleNotFoundError):
    pass


def get_importer(format: str) -> ImportParser:
    try:
        module = import_module(f"darwin.importer.formats.{format}")
        return getattr(module, "parse_path")
    except ModuleNotFoundError:
        raise ImporterNotFoundError
