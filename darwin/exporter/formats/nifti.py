import os
import shutil
from asyncore import loop
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import nibabel as nib
import numpy as np
from PIL import Image

import darwin.datatypes as dt
from darwin.utils import convert_polygons_to_mask, get_progress_bar


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
    output_volumes = None
    video_annotation = list(annotation_files)[0]
    image_id = Path(video_annotation.filename).stem
    if video_annotation is None:
        return
    if video_annotation.metadata is None:
        return
    if not video_annotation.annotations:
        return
    volume_dims, pixdim, affine = process_metadata(video_annotation.metadata)
    if affine is None or pixdim is None or volume_dims is None:
        return
    # Builds a map of class to integer
    class_map = {}
    class_count = 1
    for _, annotation in enumerate(video_annotation.annotations):
        frames = annotation.frames
        for frame_idx in frames.keys():
            class_name = frames[frame_idx].annotation_class.name
            if class_name not in class_map:
                class_map[class_name] = class_count
                class_count += 1
    # Builds output volumes per class
    if output_volumes is None:
        output_volumes = {class_name: np.zeros(volume_dims) for class_name in class_map.keys()}
    # Loops through annotations to build volumes
    for _, annotation in enumerate(video_annotation.annotations):
        frames = annotation.frames
        for frame_idx in frames.keys():
            view_idx = get_view_idx_from_slot_name(annotation.slot_names[0])
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
                frames[frame_idx].data["path"],
                height=height,
                width=width,
                pixdim=pixdims,
            )
            class_name = frames[frame_idx].annotation_class.name
            im_mask = convert_polygons_to_mask(polygon, height=height, width=width)
            output_volume = output_volumes[class_name]
            if view_idx == 0:
                output_volume[:, :, frame_idx] = np.logical_or(
                    im_mask, output_volume[:, :, frame_idx]
                )
            elif view_idx == 1:
                output_volume[:, frame_idx, :] = np.logical_or(
                    im_mask, output_volume[:, frame_idx, :]
                )
            elif view_idx == 2:
                output_volume[frame_idx, :, :] = np.logical_or(
                    im_mask, output_volume[frame_idx, :, :]
                )
    for class_name in class_map.keys():
        img = nib.Nifti1Image(
            dataobj=np.flip(output_volumes[class_name], (0, 1, 2)).astype(np.int16),
            affine=affine,
        )
        output_path = Path(output_dir) / f"{image_id}_{class_name}.nii.gz"
        nib.save(img=img, filename=output_path)


def shift_polygon_coords(polygon, height, width, pixdim):
    # Need to make it clear that we flip x/y because we need to take the transpose later.
    return [{"x": p["y"] * float(pixdim[0]), "y": p["x"] * float(pixdim[1])} for p in polygon]


def get_view_idx(frame_idx, groups):
    if groups is None:
        return 0
    for view_idx, group in enumerate(groups):
        if frame_idx in group:
            return view_idx


def get_view_idx_from_slot_name(slot_name):
    slot_names = {"0.1": 0, "0.2": 1, "0.3": 2}
    slot_names.get(slot_name, 0)
    return slot_names.get(slot_name, 0)


def process_metadata(metadata):
    volume_dims = metadata.get("shape")
    pixdim = metadata.get("pixdim")
    affine = metadata.get("affine")
    if isinstance(affine, str):
        affine = np.squeeze(np.array([eval(l) for l in affine.split("\n")]))
        if not isinstance(affine, np.ndarray):
            affine = None
    if isinstance(pixdim, str):
        pixdim = eval(pixdim)
        if not isinstance(pixdim, tuple):
            pixdim = None
    if isinstance(volume_dims, list):
        if volume_dims:
            if volume_dims[0] == 1:  # remove first singleton dimension
                volume_dims = volume_dims[1:]
        else:
            volume_dims = None
    return volume_dims, pixdim, affine
