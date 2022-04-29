from pathlib import Path
from typing import Iterator, List

from darwin.datatypes import AnnotationFile, ExportParser, PathLike
from darwin.utils import parse_darwin_json, split_video_annotation


def darwin_to_dt_gen(file_paths: List[PathLike]) -> Iterator[AnnotationFile]:
    """
    Parses the given paths recursively and into an ``Iterator`` of ``AnnotationFile``\\s.

    Parameters
    ----------
    file_paths : List[PathLike]
        The paths of the files or directories we want to parse.

    Returns
    -------
    Iterator[AnnotationFile]
        An ``Iterator`` of the parsed ``AnnotationFile``\\s.
    """
    count = 0
    for file_path in map(Path, file_paths):
        files = file_path.glob("**/*") if file_path.is_dir() else [file_path]
        for f in files:
            if f.suffix != ".json":
                continue
            data = parse_darwin_json(f, count)
            if data:
                if data.is_video:
                    for d in split_video_annotation(data):
                        d.seq = count
                        count += 1
                        yield d
                else:
                    yield data
            count += 1


def export_annotations(exporter: ExportParser, file_paths: List[PathLike], output_directory: PathLike) -> None:
    """
    Converts a set of files to a different annotation format.

    Parameters
    ----------
    exporter : ExportParser
        The parser to use.
    file_paths : List[PathLike]
        The files we want to parse.
    output_directory : PathLike
        Where the parsed files will be placed after the operation is complete.
    """
    exporter(darwin_to_dt_gen(file_paths), Path(output_directory))
    print(f"Converted annotations saved at {output_directory}")
