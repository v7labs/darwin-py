from pathlib import Path
from typing import Callable, Generator, List, Union

import darwin.datatypes as dt
from darwin.utils import parse_darwin_json, split_video_annotation


def darwin_to_dt_gen(file_paths):
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
                        yield d
                else:
                    yield data
            count += 1


def export_annotations(
    exporter: Callable[[Generator[dt.AnnotationFile, None, None], Path], None],
    file_paths: List[Union[str, Path]],
    output_directory: Union[str, Path],
):
    """Converts a set of files to a different annotation format"""
    exporter(darwin_to_dt_gen(file_paths), Path(output_directory))
    print(f"Converted annotations saved at {output_directory}")
