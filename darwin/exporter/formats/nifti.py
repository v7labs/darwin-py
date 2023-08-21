import ast
import json as native_json
from asyncore import loop
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Union

from rich.console import Console

console = Console()
try:
    import nibabel as nib
    from nibabel.orientations import axcodes2ornt, io_orientation, ornt_transform
except ImportError:
    import_fail_string = """
    You must install darwin-py with pip install darwin-py\[medical]
    in order to export using nifti format
    """
    console.print(import_fail_string)
    exit()
import numpy as np
import orjson as json
from PIL import Image

import darwin.datatypes as dt
from darwin.utils import convert_polygons_to_mask, get_progress_bar


@dataclass
class Volume:
    pixel_array: np.ndarray
    affine: Optional[np.ndarray]
    original_affine: Optional[np.ndarray]
    dims: List
    pixdims: List
    class_name: str
    series_instance_uid: str


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

    Returns
    -------
    sends output volumes, image_id and output_dir to the write_output_volume_to_disk function

    """

    video_annotations = list(annotation_files)
    for video_annotation in video_annotations:
        image_id = check_for_error_and_return_imageid(video_annotation, output_dir)
        if not isinstance(image_id, str):
            continue
        output_volumes = build_output_volumes(video_annotation)
        slot_map = {slot.name: slot for slot in video_annotation.slots}
        for annotation in video_annotation.annotations:
            populate_output_volumes(annotation, output_dir, slot_map, output_volumes, image_id)
        write_output_volume_to_disk(output_volumes, image_id=image_id, output_dir=output_dir)


def build_output_volumes(video_annotation: dt.AnnotationFile):
    """
    This is a function to create the output volumes based on the whole annotation file

    Parameters
    ----------
    video_annotation : dt.AnnotationFile

    Returns
    -------
    output_volumes: Dict
        The output volume built per class

    """
    # Builds a map of class to integer
    class_map = {}
    class_count = 1
    for annotation in video_annotation.annotations:
        frames = annotation.frames
        for frame_idx in frames.keys():
            class_name = frames[frame_idx].annotation_class.name
            if class_name not in class_map:
                class_map[class_name] = class_count
                class_count += 1

    output_volumes = {}
    for slot in video_annotation.slots:
        slot_metadata = slot.metadata
        series_instance_uid = slot_metadata.get("SeriesInstanceUID", "SeriesIntanceUIDNotProvided")
        # Builds output volumes per class
        volume_dims, pixdims, affine, original_affine = process_metadata(slot.metadata)
        output_volumes[series_instance_uid] = {
            class_name: Volume(
                pixel_array=np.zeros(volume_dims),
                affine=affine,
                original_affine=original_affine,
                dims=volume_dims,
                pixdims=pixdims,
                series_instance_uid=series_instance_uid,
                class_name=class_name,
            )
            for class_name in class_map.keys()
        }
    return output_volumes


def check_for_error_and_return_imageid(video_annotation: dt.AnnotationFile, output_dir: Path):
    """
    Given the video_annotation file and the output directory, checks for a range of errors and
    returns messages accordingly.

    Parameters
    ----------
    video_annotation : dt.AnnotationFile
        The ``AnnotationFile``\\s to be exported.
    output_dir : Path
        The folder where the new instance mask files will be.

    Returns
    -------
    image_id : str

    """

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

    for slot in video_annotation.slots:
        # Pick the first slot to take the metadata from. We assume that all slots have the same metadata.
        metadata = slot.metadata
        if metadata is None:
            return create_error_message_json(
                f"No metadata found for {str(filename)}, are you sure this is medical data?", output_dir, image_id
            )

        volume_dims, pixdim, affine, _ = process_metadata(metadata)
        if affine is None or pixdim is None or volume_dims is None:
            return create_error_message_json(
                f"Missing one of affine, pixdim or shape in metadata for {str(filename)}, try reuploading file",
                output_dir,
                image_id,
            )
    return image_id


def populate_output_volumes(
    annotation: Union[dt.Annotation, dt.VideoAnnotation],
    output_dir: str,
    slot_map: Dict,
    output_volumes: Dict,
    image_id: str,
) -> None:
    """
    Exports the given ``AnnotationFile``\\s into nifti format inside of the given
    ``output_dir``. Deletes everything within ``output_dir/masks`` before writting to it.

    Parameters
    ----------
    annotation : Union[dt.Annotation, dt.VideoAnnotation]
        The Union of these two files used to populate the volume with
    output_dir : Path
        The folder where the new instance mask files will be.
    slot_map : Dict
        Dictionary of the different slots within the annotation file
    output_volumes : Dict
        volumes created from the build_output_volumes file
    image_id : str

    Returns
    -------
    volume : dict
        Returns the populated volume

    """

    slot_name = annotation.slot_names[0]
    slot = slot_map[slot_name]
    series_instance_uid = slot.metadata.get("SeriesInstanceUID", "SeriesIntanceUIDNotProvided")
    volume = output_volumes.get(series_instance_uid)
    frames = annotation.frames
    frame_new = {}

    # define the different planes
    XYPLANE = 0
    XZPLANE = 1
    YZPLANE = 2

    for frame_idx in frames.keys():
        frame_new[frame_idx] = frames
        view_idx = get_view_idx_from_slot_name(slot_name, slot.metadata.get("orientation"))
        if view_idx == XYPLANE:
            height, width = (
                volume[annotation.annotation_class.name].dims[0],
                volume[annotation.annotation_class.name].dims[1],
            )
        elif view_idx == XZPLANE:
            height, width = (
                volume[annotation.annotation_class.name].dims[0],
                volume[annotation.annotation_class.name].dims[2],
            )
        elif view_idx == YZPLANE:
            height, width = (
                volume[annotation.annotation_class.name].dims[1],
                volume[annotation.annotation_class.name].dims[2],
            )
        if "paths" in frames[frame_idx].data:
            # Dealing with a complex polygon
            polygons = [
                shift_polygon_coords(polygon_path, volume[annotation.annotation_class.name].pixdims)
                for polygon_path in frames[frame_idx].data["paths"]
            ]
        elif "path" in frames[frame_idx].data:
            # Dealing with a simple polygon
            polygons = shift_polygon_coords(
                frames[frame_idx].data["path"], volume[annotation.annotation_class.name].pixdims
            )
        else:
            continue
        class_name = frames[frame_idx].annotation_class.name
        im_mask = convert_polygons_to_mask(polygons, height=height, width=width)
        volume = output_volumes[series_instance_uid]
        if view_idx == 0:
            volume[annotation.annotation_class.name].pixel_array[:, :, frame_idx] = np.logical_or(
                im_mask, volume[annotation.annotation_class.name].pixel_array[:, :, frame_idx]
            )
        elif view_idx == 1:
            volume[annotation.annotation_class.name].pixel_array[:, frame_idx, :] = np.logical_or(
                im_mask, volume[annotation.annotation_class.name].pixel_array[:, frame_idx, :]
            )
        elif view_idx == 2:
            volume[annotation.annotation_class.name].pixel_array[frame_idx, :, :] = np.logical_or(
                im_mask, volume[annotation.annotation_class.name].pixel_array[frame_idx, :, :]
            )


def write_output_volume_to_disk(output_volumes: Dict, image_id: str, output_dir: str):
    # volumes are the values of this nested dict
    def unnest_dict_to_list(d):
        result = []
        for value in d.values():
            if isinstance(value, dict):
                result.extend(unnest_dict_to_list(value))
            else:
                result.append(value)
        return result

    volumes = unnest_dict_to_list(output_volumes)
    for volume in volumes:
        img = nib.Nifti1Image(
            dataobj=np.flip(volume.pixel_array, (0, 1, 2)).astype(np.int16),
            affine=volume.affine,
        )
        if volume.original_affine is not None:
            orig_ornt = io_orientation(volume.original_affine)  # Get orientation of current affine
            img_ornt = io_orientation(volume.affine)  # Get orientation of RAS affine
            from_canonical = ornt_transform(img_ornt, orig_ornt)  # Get transform from RAS to current affine
            img = img.as_reoriented(from_canonical)
        output_path = Path(output_dir) / f"{image_id}_{volume.series_instance_uid}_{volume.class_name}.nii.gz"
        if not output_path.parent.exists():
            output_path.parent.mkdir(parents=True)
        nib.save(img=img, filename=output_path)


def shift_polygon_coords(polygon, pixdim):
    # Need to make it clear that we flip x/y because we need to take the transpose later.
    if pixdim[1] > pixdim[0]:
        return [{"x": p["y"], "y": p["x"] * pixdim[1] / pixdim[0]} for p in polygon]
    elif pixdim[1] < pixdim[0]:
        return [{"x": p["y"] * pixdim[0] / pixdim[1], "y": p["x"]} for p in polygon]
    else:
        return [{"x": p["y"], "y": p["x"]} for p in polygon]


def get_view_idx(frame_idx, groups):
    if groups is None:
        return 0
    for view_idx, group in enumerate(groups):
        if frame_idx in group:
            return view_idx


def get_view_idx_from_slot_name(slot_name, orientation):
    if orientation is None:
        orientation_dict = {"0.1": 0, "0.2": 1, "0.3": 2}
        return orientation_dict.get(slot_name, 0)
    else:
        orientation_dict = {"AXIAL": 0, "SAGITTAL": 1, "CORONAL": 2}
        return orientation_dict.get(orientation, 0)


def process_metadata(metadata):
    volume_dims = metadata.get("shape")
    pixdim = metadata.get("pixdim")
    affine = process_affine(metadata.get("affine"))
    original_affine = process_affine(metadata.get("original_affine"))
    # If the original affine is in the medical payload of metadata then use it
    if isinstance(pixdim, str):
        pixdim = ast.literal_eval(pixdim)
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
    return volume_dims, pixdim, affine, original_affine


def process_affine(affine):
    if isinstance(affine, str):
        affine = np.squeeze(np.array([ast.literal_eval(l) for l in affine.split("\n")]))
    elif isinstance(affine, list):
        affine = np.array(affine).astype(float)
    else:
        return
    if isinstance(affine, np.ndarray):
        return affine


def create_error_message_json(error_message: str, output_dir: str, image_id: str):
    output_path = Path(output_dir) / f"{image_id}_error.json"
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True)
    with open(output_path, "w") as f:
        native_json.dump({"error": error_message}, f)

    return False
