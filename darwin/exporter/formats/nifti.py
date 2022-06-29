import os
import shutil
from pathlib import Path
from typing import Iterable

import nibabel as nib
import numpy as np
from PIL import Image
from tests.darwin.exporter.formats.export_nifti_test import video_annotation

import darwin.datatypes as dt
from darwin.utils import (
    convert_polygons_to_mask,
    get_progress_bar,
    ispolygon,
    parse_darwin_json,
)


def export(annotation_files: Iterable[dt.AnnotationFile], output_dir: Path) -> None:
    """
    Exports the given ``AnnotationFile``\\s into nifti format inside of the given
    ``output_dir``. Deletes everything within ``output_dir/masks`` before writting to it.

    Parameters
    ----------
    annotation_files : Iterable[dt.AnnotationFile]
        The ``AnnotationFile``\\s to be exported.
    output_dir : Path
        The folder where the new instance mask files will be.
    """
    for video_annotation in get_progress_bar(list(annotation_files), "Processing annotations"):
        image_id = os.path.splitext(video_annotation.filename)[0]
        # video_annotation = parse_darwin_json(Path(annotation_file))
        if video_annotation is None:
            continue
        if video_annotation.groups is None or video_annotation.shape is None or video_annotation.affine is None:
            continue
        groups = video_annotation.groups
        volume_dims = video_annotation.shape
        pixdim = video_annotation.pixdim
        print(pixdim)
        print(pixdim[0])
        output_volume = np.zeros(volume_dims)
        for _, annotation in enumerate(video_annotation.annotations):
            frames = annotation.frames
            for frame_idx in frames.keys():
                view_idx = get_view_idx(frame_idx=frame_idx, groups=groups)
                if view_idx == 0:
                    height, width = volume_dims[0], volume_dims[1]
                    pixdims = [pixdim[0], pixdim[1]]
                elif view_idx == 1:
                    height, width = volume_dims[0], volume_dims[2]
                    pixdims = [pixdim[0], pixdim[2]]
                elif view_idx == 2:
                    height, width = volume_dims[1], volume_dims[2]
                    pixdims = [pixdim[1], pixdim[2]]
                polygon = shift_polygon_coords(
                    frames[frame_idx].data["path"], height=height, width=width, pixdim=pixdims
                )
                im_mask = convert_polygons_to_mask(polygon, height=height, width=width)
                slice_idx = groups[view_idx].index(frame_idx)
                if view_idx == 0:
                    output_volume[:, :, slice_idx] = np.logical_or(im_mask, output_volume[:, :, slice_idx])
                elif view_idx == 1:
                    output_volume[:, slice_idx, :] = np.logical_or(im_mask, output_volume[:, slice_idx, :])
                elif view_idx == 2:
                    output_volume[slice_idx, :, :] = np.logical_or(im_mask, output_volume[slice_idx, :, :])
        img = nib.Nifti1Image(
            dataobj=np.flip(output_volume, (0, 1, 2)).astype(np.int16), affine=video_annotation.affine
        )
        output_path = Path(output_dir) / f"{image_id}.nii.gz"
        nib.save(img=img, filename=output_path)


def shift_polygon_coords(polygon, height, width, pixdim):
    # Need to make it clear that we flip x/y because we need to take the transpose later.
    return [{"x": p["y"] * float(pixdim[0]), "y": p["x"] * float(pixdim[1])} for p in polygon]


def get_view_idx(frame_idx, groups):
    for view_idx, group in enumerate(groups):
        if frame_idx in group:
            return view_idx
