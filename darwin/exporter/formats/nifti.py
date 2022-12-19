import json as native_json
from asyncore import loop
from pathlib import Path
from typing import Iterable

import nibabel as nib
import numpy as np
import orjson as json
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
    video_annotations = list(annotation_files)
    for video_annotation in video_annotations:
        export_single_nifti_file(video_annotation, output_dir)


def export_single_nifti_file(video_annotation: dt.AnnotationFile, output_dir: Path) -> None:
    output_volumes = None
    filename = Path(video_annotation.filename)
    suffixes = filename.suffixes
    if len(suffixes) > 2:
        return create_error_message_json(
            "Misconfigured filename, contains too many suffixes", output_dir, str(filename)
        )
    elif len(suffixes) == 2:
        if suffixes[0] == ".nii" and suffixes[1] == ".gz":
            image_id = str(filename).strip("".join(suffixes))
        else:
            return create_error_message_json("Two suffixes found but not ending in .nii.gz", output_dir, str(filename))
    elif len(suffixes) == 1:
        if suffixes[0] == ".nii" or suffixes[0] == ".dcm":
            image_id = filename.stem
        else:
            return create_error_message_json(
                "Misconfigured filename, not ending in .nii or .dcm. Are you sure this is medical data?",
                output_dir,
                str(filename),
            )
    else:
        return create_error_message_json(
            "You are trying to export to nifti. Filename should contain either .nii, .nii.gz or .dcm extension."
            "Are you sure this is medical data?",
            output_dir,
            str(filename),
        )
    if video_annotation is None:
        return create_error_message_json("video_annotation not found", output_dir, image_id)
    # Pick the first slot to take the metadata from. We assume that all slots have the same metadata.
    metadata = video_annotation.slots[0].metadata
    if metadata is None:
        return create_error_message_json(
            f"No metadata found for {str(filename)}, are you sure this is medical data?", output_dir, image_id
        )
    volume_dims, pixdim, affine = process_metadata(metadata)
    if affine is None or pixdim is None or volume_dims is None:
        return create_error_message_json(
            f"Missing one of affine, pixdim or shape in metadata for {str(filename)}, try reuploading file",
            output_dir,
            image_id,
        )
    if not video_annotation.annotations:
        create_empty_nifti_file(volume_dims, affine, output_dir, image_id)
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
            if "paths" in frames[frame_idx].data:
                # Dealing with a complex polygon
                polygons = [
                    shift_polygon_coords(
                        polygon_path,
                        height=height,
                        width=width,
                        pixdim=pixdims,
                    )
                    for polygon_path in frames[frame_idx].data["paths"]
                ]
            elif "path" in frames[frame_idx].data:
                # Dealing with a simple polygon
                polygons = shift_polygon_coords(
                    frames[frame_idx].data["path"],
                    height=height,
                    width=width,
                    pixdim=pixdims,
                )
            else:
                continue
            class_name = frames[frame_idx].annotation_class.name
            im_mask = convert_polygons_to_mask(polygons, height=height, width=width)
            output_volume = output_volumes[class_name]
            if view_idx == 0:
                output_volume[:, :, frame_idx] = np.logical_or(im_mask, output_volume[:, :, frame_idx])
            elif view_idx == 1:
                output_volume[:, frame_idx, :] = np.logical_or(im_mask, output_volume[:, frame_idx, :])
            elif view_idx == 2:
                output_volume[frame_idx, :, :] = np.logical_or(im_mask, output_volume[frame_idx, :, :])
    for class_name in class_map.keys():
        img = nib.Nifti1Image(
            dataobj=np.flip(output_volumes[class_name], (0, 1, 2)).astype(np.int16),
            affine=affine,
        )
        output_path = Path(output_dir) / f"{image_id}_{class_name}.nii.gz"
        if not output_path.parent.exists():
            output_path.parent.mkdir(parents=True)
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
        if isinstance(pixdim, tuple) or isinstance(pixdim, list):
            if len(pixdim) == 4:
                pixdim = pixdim[1:]
            if len(pixdim) != 3:
                pixdim = None
        else:
            pixdim = None
    if isinstance(volume_dims, list):
        if volume_dims:
            if volume_dims[0] == 1:  # remove first singleton dimension
                volume_dims = volume_dims[1:]
        else:
            volume_dims = None
    return volume_dims, pixdim, affine


def create_error_message_json(error_message, output_dir, image_id: str):
    output_path = Path(output_dir) / f"{image_id}_error.json"
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True)
    with open(output_path, "w") as f:
        native_json.dump({"error": error_message}, f)


def create_empty_nifti_file(volume_dims, affine, output_dir, image_id: str):
    output_path = Path(output_dir) / f"{image_id}_empty.nii.gz"
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True)
    img = nib.Nifti1Image(dataobj=np.flip(np.zeros(volume_dims), (0, 1, 2)).astype(np.int16), affine=affine)
    nib.save(img=img, filename=output_path)
