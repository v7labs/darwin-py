import json
from datetime import date
from pathlib import Path
from typing import Generator, List

import numpy as np

import darwin.datatypes as dt


def export(annotation_files: Generator[dt.AnnotationFile, None, None], output_dir: Path):
    raise NotImplementedError
