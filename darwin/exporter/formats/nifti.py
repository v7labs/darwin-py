import ast
import json as native_json
import re
from dataclasses import dataclass
from enum import Enum
from numbers import Number
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union

from rich.console import Console

console = Console()
try:
    import nibabel as nib
    from nibabel.orientations import io_orientation, ornt_transform
except ImportError:
    import_fail_string = r"""
    You must install darwin-py with pip install darwin-py\[medical]
    in order to export using nifti format
    """
    console.print(import_fail_string)
    exit()
import numpy as np

import darwin.datatypes as dt
from darwin.utils import convert_polygons_to_mask


class Plane(Enum):
    XY = 0
    XZ = 1
    YZ = 2


@dataclass
class Volume:
    pixel_array: np.ndarray
    affine: Optional[np.ndarray]
    original_affine: Optional[np.ndarray]
    dims: List
    pixdims: List
    class_name: str
    series_instance_uid: str
    from_raster_layer: bool


def export(
    annotation_files: Iterable[dt.AnnotationFile],
    output_dir: Path,
    legacy: bool = False,
) -> None:
    """
    Exports the given ``AnnotationFile``\\s into nifti format inside of the given
    ``output_dir``. Deletes everything within ``output_dir/masks`` before writting to it.

    Parameters
    ----------
    annotation_files : Iterable[dt.AnnotationFile]
        The ``AnnotationFile``\\s to be exported.
    output_dir : Path
        The folder where the new instance mask files will be.
    legacy : bool, default=False
        If ``True``, the exporter will use the legacy calculation.
        If ``False``, the exporter will use the new calculation by dividing with pixdims.


    Returns
    -------
    sends output volumes, image_id and output_dir to the write_output_volume_to_disk function

    """

    if legacy:
        console.print(
            "Legacy flag is set to True. Annotations will be resized using legacy calculations.",
            style="bold blue",
        )

    video_annotations = list(annotation_files)
    for video_annotation in video_annotations:
        image_id = check_for_error_and_return_imageid(video_annotation, output_dir)
        if not isinstance(image_id, str):
            continue
        polygon_class_names = [
            ann.annotation_class.name
            for ann in video_annotation.annotations
            if ann.annotation_class.annotation_type == "polygon"
        ]
        # Check if there are any rasters in the annotation, these are created with a _m suffix
        # in addition to those created from polygons.
        annotation_types = [
            a.annotation_class.annotation_type for a in video_annotation.annotations
        ]
        mask_present = "raster_layer" in annotation_types and "mask" in annotation_types
        output_volumes = build_output_volumes(
            video_annotation,
            class_names_to_export=polygon_class_names,
            from_raster_layer=False,
            mask_present=mask_present,
        )
        slot_map = {slot.name: slot for slot in video_annotation.slots}
        polygon_annotations = [
            ann
            for ann in video_annotation.annotations
            if ann.annotation_class.annotation_type == "polygon"
        ]
        if polygon_annotations:
            populate_output_volumes_from_polygons(
                polygon_annotations, slot_map, output_volumes, legacy=legacy
            )
        write_output_volume_to_disk(
            output_volumes, image_id=image_id, output_dir=output_dir, legacy=legacy
        )
        # Need to map raster layers to SeriesInstanceUIDs
        if mask_present:
            mask_id_to_classname = {
                ann.id: ann.annotation_class.name
                for ann in video_annotation.annotations
                if ann.annotation_class.annotation_type == "mask"
            }
            raster_output_volumes = build_output_volumes(
                video_annotation,
                class_names_to_export=list(mask_id_to_classname.values()),
                from_raster_layer=True,
            )

            # This assumes only one raster_layer annotation. If we allow multiple raster layers per annotation file we need to change this.
            raster_layer_annotation = [
                ann
                for ann in video_annotation.annotations
                if ann.annotation_class.annotation_type == "raster_layer"
            ][0]
            if raster_layer_annotation:
                populate_output_volumes_from_raster_layer(
                    annotation=raster_layer_annotation,
                    mask_id_to_classname=mask_id_to_classname,
                    slot_map=slot_map,
                    output_volumes=raster_output_volumes,
                )
            write_output_volume_to_disk(
                raster_output_volumes,
                image_id=image_id,
                output_dir=output_dir,
                legacy=legacy,
            )


def build_output_volumes(
    video_annotation: dt.AnnotationFile,
    from_raster_layer: bool = False,
    class_names_to_export: List[str] = None,
    mask_present: Optional[bool] = False,
) -> Dict:
    """
    This is a function to create the output volumes based on the whole annotation file

    Parameters
    ----------
    video_annotation : dt.AnnotationFile
        The ``AnnotationFile``\\s to be exported.
    from_raster_layer : bool
        Whether the output volumes are being built from raster layers or not
    class_names_to_export : List[str]
        The list of class names to export
    mask_present: bool
        If mask annotations are present in the annotation
    Returns
    -------
    output_volumes: Dict
        The output volume built per class

    """
    # Builds a map of class to integer, if its a polygon we use the class name as is
    # for the mask annotations we append a suffix _m to ensure backwards compatibility

    output_volumes = {}
    for slot in video_annotation.slots:
        slot_metadata = slot.metadata
        assert slot_metadata is not None
        series_instance_uid = slot_metadata.get(
            "SeriesInstanceUID", "SeriesIntanceUIDNotProvided"
        )
        # Builds output volumes per class
        volume_dims, pixdims, affine, original_affine = process_metadata(slot.metadata)
        if not mask_present and not class_names_to_export:
            class_names_to_export = [
                ""
            ]  # If there are no annotations to export, we still need to create an empty volume
        output_volumes[series_instance_uid] = {
            class_name: Volume(
                pixel_array=np.zeros(volume_dims),
                affine=affine,
                original_affine=original_affine,
                dims=volume_dims,
                pixdims=pixdims,
                series_instance_uid=series_instance_uid,
                class_name=class_name,
                from_raster_layer=from_raster_layer,
            )
            for class_name in class_names_to_export
        }
    return output_volumes


def check_for_error_and_return_imageid(
    video_annotation: dt.AnnotationFile, output_dir: Path
) -> Union[str, bool]:
    """Given the video_annotation file and the output directory, checks for a range of errors and
    returns messages accordingly.

    Parameters
    ----------
    video_annotation : dt.AnnotationFile
        The ``AnnotationFile``\\s to be exported.
    output_dir : Path
        The folder where the new instance mask files will be.

    Returns
    -------
    Union[str, bool]
        Returns the image_id if no errors are found, otherwise returns False
    """
    # Check if all item slots have the correct file-extension
    for slot in video_annotation.slots:
        for source_file in slot.source_files:
            filename = Path(source_file["file_name"])
            if not (
                filename.name.lower().endswith(".nii.gz")
                or filename.name.lower().endswith(".nii")
                or filename.name.lower().endswith(".dcm")
            ):
                return create_error_message_json(
                    "Misconfigured filename, not ending in .nii, .nii.gz or .dcm. Are you sure this is medical data?",
                    output_dir,
                    str(filename),
                )

    filename = Path(video_annotation.filename)
    if filename.name.lower().endswith(".nii.gz"):
        image_id = re.sub(r"(?i)\.nii\.gz$", "", str(filename))
    elif filename.name.lower().endswith(".nii"):
        image_id = re.sub(r"(?i)\.nii$", "", str(filename))
    elif filename.name.lower().endswith(".dcm"):
        image_id = re.sub(r"(?i)\.dcm$", "", str(filename))
    else:
        image_id = str(filename)

    if video_annotation is None:
        return create_error_message_json(
            "video_annotation not found", output_dir, image_id
        )
    if video_annotation is None:
        return create_error_message_json(
            "video_annotation not found", output_dir, image_id
        )

    for slot in video_annotation.slots:
        # Pick the first slot to take the metadata from. We assume that all slots have the same metadata.
        metadata = slot.metadata
        if metadata is None:
            return create_error_message_json(
                f"No metadata found for {str(filename)}, are you sure this is medical data?",
                output_dir,
                image_id,
            )

        volume_dims, pixdim, affine, _ = process_metadata(metadata)
        if affine is None or pixdim is None or volume_dims is None:
            return create_error_message_json(
                f"Missing one of affine, pixdim or shape in metadata for {str(filename)}, try reuploading file",
                output_dir,
                image_id,
            )
    return image_id


def update_pixel_array(
    volume: Dict,
    annotation_class_name: str,
    im_mask: np.ndarray,
    plane: Plane,
    frame_idx: int,
) -> Dict:
    """Updates the pixel array of the given volume with the given mask.

    Parameters
    ----------
    volume : Dict
        Volume with pixel array to be updated
    annotation_class_name : str
        Name of the annotation class
    im_mask : np.ndarray
        Mask to be added to the pixel array
    plane : Plane
        Plane of the mask
    frame_idx : int
        Frame index of the mask

    Returns
    -------
    Dict
        Updated volume
    """
    plane_to_slice = {
        Plane.XY: np.s_[:, :, frame_idx],
        Plane.XZ: np.s_[:, frame_idx, :],
        Plane.YZ: np.s_[frame_idx, :, :],
    }
    if plane in plane_to_slice:
        slice_ = plane_to_slice[plane]
        volume[annotation_class_name].pixel_array[slice_] = np.logical_or(
            im_mask,
            volume[annotation_class_name].pixel_array[slice_],
        )
    return volume


def populate_output_volumes_from_polygons(
    annotations: List[Union[dt.Annotation, dt.VideoAnnotation]],
    slot_map: Dict,
    output_volumes: Dict,
    legacy: bool = False,
):
    """
    Populates the output volumes with the given polygon annotations. The annotations are converted into masks
    and added to the corresponding volume based on the series instance UID.

    Parameters
    ----------
    annotations : List[Union[dt.Annotation, dt.VideoAnnotation]]
        List of polygon annotations used to populate the volume with
    slot_map : Dict
        Dictionary of the different slots within the annotation file
    output_volumes : Dict
        Volumes created from the build_output_volumes file
    legacy : bool, default=False
        If ``True``, the exporter will use the legacy calculation.
        If ``False``, the exporter will use the new calculation by dividing with pixdims.
    """
    for annotation in annotations:
        slot_name = annotation.slot_names[0]
        slot = slot_map[slot_name]
        series_instance_uid = slot.metadata.get(
            "SeriesInstanceUID", "SeriesIntanceUIDNotProvided"
        )
        volume = output_volumes.get(series_instance_uid)
        frames = annotation.frames

        for frame_idx in frames.keys():
            plane = get_plane_from_slot_name(
                slot_name, slot.metadata.get("orientation")
            )
            dims = volume[annotation.annotation_class.name].dims
            if plane == Plane.XY:
                height, width = dims[0], dims[1]
            elif plane == Plane.XZ:
                height, width = dims[0], dims[2]
            elif plane == Plane.YZ:
                height, width = dims[1], dims[2]
            pixdims = volume[annotation.annotation_class.name].pixdims
            frame_data = frames[frame_idx].data
            if "paths" in frame_data:
                # Dealing with a complex polygon
                polygons = [
                    shift_polygon_coords(polygon_path, pixdims, legacy=legacy)
                    for polygon_path in frame_data["paths"]
                ]
            else:
                continue
            im_mask = convert_polygons_to_mask(polygons, height=height, width=width)
            volume = update_pixel_array(
                output_volumes[series_instance_uid],
                annotation.annotation_class.name,
                im_mask,
                plane,
                frame_idx,
            )


def populate_output_volumes_from_raster_layer(
    annotation: dt.Annotation,
    mask_id_to_classname: Dict,
    slot_map: Dict,
    output_volumes: Dict,
) -> Dict:
    """
    Populates the output volumes provided with the raster layer annotations

    Parameters
    ----------
    annotation : Union[dt.Annotation, dt.VideoAnnotation]
        The Union of these two files used to populate the volume with
    mask_id_to_classname : Dict
        Map from mask id to class names
    slot_map: Dict
        Dictionary of the different slots within the annotation file
    output_volumes : Dict
        volumes created from the build_output_volumes file

    Returns
    -------
    volume : dict
        Returns dict of volumes with class names as keys and volumes as values
    """
    slot_name = annotation.slot_names[0]
    slot = slot_map[slot_name]
    series_instance_uid = slot.metadata.get(
        "SeriesInstanceUID", "SeriesIntanceUIDNotProvided"
    )
    volume = output_volumes.get(series_instance_uid)
    frames = annotation.frames
    mask_annotation_ids_mapping = {}
    multilabel_volume = np.zeros(slot.metadata["shape"][1:])
    for frame_idx in sorted(frames.keys()):
        frame_idx = int(frame_idx)
        frame_data = annotation.frames[frame_idx]
        dense_rle = frame_data.data["dense_rle"]
        mask_2d = decode_rle(dense_rle, slot.width, slot.height)
        multilabel_volume[:, :, frame_idx] = mask_2d.T
        mask_annotation_ids_mapping.update(
            frame_data.data["mask_annotation_ids_mapping"]
        )
    # Now we convert this multilabel array into this dictionary of output volumes
    # in order to re-use the write_output_volume_to_disk function.
    for mask_id, class_name in mask_id_to_classname.items():
        volume = output_volumes[series_instance_uid]
        mask_int_id = mask_annotation_ids_mapping[mask_id]
        # We want to create a binary mask for each class
        volume[class_name].pixel_array = np.where(
            multilabel_volume == int(mask_int_id), 1, volume[class_name].pixel_array
        )
    return volume


def write_output_volume_to_disk(
    output_volumes: Dict,
    image_id: str,
    output_dir: Union[str, Path],
    legacy: bool = False,
) -> None:
    """Writes the given output volumes to disk.

    Parameters
    ----------
    output_volumes : Dict
        Output volumes to be written to disk
    image_id : str
        The specific image id
    output_dir : Union[str, Path]
        The output directory to write the volumes to
    legacy : bool, default=False
        If ``True``, the exporter will use the legacy calculation.
        If ``False``, the exporter will use the new calculation by dividing with pixdims.

    Returns
    -------
    None
    """

    # volumes are the values of this nested dict
    def unnest_dict_to_list(d: Dict) -> List:
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
        if legacy and volume.original_affine is not None:
            orig_ornt = io_orientation(
                volume.original_affine
            )  # Get orientation of current affine
            img_ornt = io_orientation(volume.affine)  # Get orientation of RAS affine
            from_canonical = ornt_transform(
                img_ornt, orig_ornt
            )  # Get transform from RAS to current affine
            img = img.as_reoriented(from_canonical)
        if volume.from_raster_layer:
            output_path = Path(output_dir) / f"{image_id}_{volume.class_name}_m.nii.gz"
        else:
            output_path = Path(output_dir) / f"{image_id}_{volume.class_name}.nii.gz"
        if not output_path.parent.exists():
            output_path.parent.mkdir(parents=True)
        nib.save(img=img, filename=output_path)


def shift_polygon_coords(
    polygon: List[Dict], pixdim: List[Number], legacy: bool = False
) -> List:
    if legacy:
        # Need to make it clear that we flip x/y because we need to take the transpose later.
        if pixdim[1] > pixdim[0]:
            return [{"x": p["y"], "y": p["x"] * pixdim[1] / pixdim[0]} for p in polygon]
        elif pixdim[1] < pixdim[0]:
            return [{"x": p["y"] * pixdim[0] / pixdim[1], "y": p["x"]} for p in polygon]
        else:
            return [{"x": p["y"], "y": p["x"]} for p in polygon]
    else:
        return [{"x": p["y"] // pixdim[1], "y": p["x"] // pixdim[0]} for p in polygon]


def get_view_idx(frame_idx: int, groups: List) -> int:
    """Returns the view index for the given frame index and groups.

    Parameters
    ----------
    frame_idx : int
        Frame index
    groups : List
        List of groups

    Returns
    -------
    int
        View index
    """
    if groups is None:
        return 0
    for view_idx, group in enumerate(groups):
        if frame_idx in group:
            return view_idx


def get_plane_from_slot_name(slot_name: str, orientation: Union[str, None]) -> Plane:
    """Returns the plane from the given slot name and orientation.

    Parameters
    ----------
    slot_name : str
        Slot name
    orientation : Union[str, None]
        Orientation

    Returns
    -------
    Plane
        Enum representing the plane
    """
    if orientation is None:
        orientation_dict = {"0.1": 0, "0.2": 1, "0.3": 2}
        return Plane(orientation_dict.get(slot_name, 0))
    orientation_dict = {"AXIAL": 0, "SAGITTAL": 1, "CORONAL": 2}
    return Plane(orientation_dict.get(orientation, 0))


def process_metadata(metadata: Dict) -> Tuple:
    """Processes the metadata and returns the volume dimensions, pixel dimensions, affine and original affine.

    Parameters
    ----------
    metadata : Dict
        Metadata to be processed

    Returns
    -------
    Tuple
        Tuple containing volume dimensions, pixel dimensions, affine and original affine
    """
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


def process_affine(affine: Union[str, List, np.ndarray]) -> Optional[np.ndarray]:
    """Converts affine to numpy array if it is not already.

    Parameters
    ----------
    affine : Union[str, List, np.ndarray]
        affine object to be converted

    Returns
    -------
    Optional[np.ndarray]
        affine as numpy array
    """
    if isinstance(affine, str):
        affine = np.squeeze(
            np.array([ast.literal_eval(lst) for lst in affine.split("\n")])
        )
    elif isinstance(affine, list):
        affine = np.array(affine).astype(float)
    else:
        return
    if isinstance(affine, np.ndarray):
        return affine


def create_error_message_json(
    error_message: str, output_dir: Union[str, Path], image_id: str
) -> bool:
    """Creates a json file with the given error message.

    Parameters
    ----------
    error_message : str
        Error message to be written to the file
    output_dir : Union[str, Path]
        Output directory
    image_id : str
        Associated image id

    Returns
    -------
    bool
        Always returns False
    """
    output_path = Path(output_dir) / f"{image_id}_error.json"
    if not output_path.parent.exists():
        output_path.parent.mkdir(parents=True)
    with open(output_path, "w") as f:
        native_json.dump({"error": error_message}, f)

    return False


def decode_rle(rle_data: List[int], width: int, height: int) -> np.ndarray:
    """Decodes run-length encoding (RLE) data into a mask array.

    Parameters
    ----------
    rle_data : List[int]
        List of RLE data
    width : int
        Width of the data
    height : int
        Height of the data

    Returns
    -------
    np.ndarray
        RLE data
    """
    total_pixels = width * height
    mask = np.zeros(total_pixels, dtype=np.uint8)
    pos = 0
    for i in range(0, len(rle_data), 2):
        value = rle_data[i]
        length = rle_data[i + 1]
        mask[pos : pos + length] = value
        pos += length
    return mask.reshape(height, width)
