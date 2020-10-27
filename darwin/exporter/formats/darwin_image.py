import shutil
from pathlib import Path
from typing import Generator

import numpy as np
from PIL import Image

import darwin.datatypes as dt
from darwin.utils import convert_polygons_to_mask, get_progress_bar, ispolygon


def export(annotation_files: Generator[dt.AnnotationFile, None, None], output_dir: Path):
    for annotation_file in get_progress_bar(list(annotation_files), "Processing annotations"):
        import pdb; pdb.set_trace()  # XXX BREAKPOINT
        pass
