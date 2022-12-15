import warnings
import zipfile
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Union

import orjson as json
from rich.console import Console

console = Console()
try:
    import cc3d
    import nibabel as nib
except ImportError:
    import_fail_string = """
    You must install darwin-py with pip install darwin-py\[medical]
    in order to import with using nifti format
    """
    console.print(import_fail_string)
    exit()
import numpy as np
from jsonschema import validate
from upolygon import find_contours

import darwin.datatypes as dt
from darwin.importer.formats.nifti_schemas import nifti_import_schema
from darwin.version import __version__


def parse_path(path: Path) -> Optional[List[dt.AnnotationFile]]:
    """
    Parses the given ``nifti`` file and returns a ``List[dt.AnnotationFile]`` with the parsed
    information.

    Parameters
    ----------
    path : Path
        The ``Path`` to the ``nifti`` file.

    Returns
    -------
    Optional[List[dt.AnnotationFile]]
        Returns ``None`` if the given file is not in ``json`` format, or ``List[dt.AnnotationFile]``
        otherwise.
    """
    if not isinstance(path, Path):
        path = Path(path)
    if path.suffix != ".json":
        console.print("Skipping file: {} (not a json file)".format(path), style="bold yellow")
        return None
    with open(path, "r") as f:
        data = json.loads(f.read())
        try:
            validate(data, schema=nifti_import_schema)
        except Exception as e:
            console.print(
                "Skipping file: {} (invalid json file, see schema for details)".format(path), style="bold yellow"
            )
            return None
    nifti_annotations = data.get("data")
    if nifti_annotations is None or nifti_annotations == []:
        console.print("Skipping file: {} (no data found)".format(path), style="bold yellow")
        return None
    annotation_files = []
    for nifti_annotation in nifti_annotations:
        annotation_file = _parse_nifti(
            Path(nifti_annotation["label"]),
            nifti_annotation["image"],
            path,
            class_map=nifti_annotation.get("class_map"),
            mode=nifti_annotation.get("mode", "image"),
        )
        annotation_files.append(annotation_file)
    return annotation_files


def _parse_nifti(nifti_path: Path, filename: Path, json_path: Path, class_map: Dict, mode: str) -> dt.AnnotationFile:

    img: np.ndarray = process_nifti(nib.load(nifti_path))

    shape = img.shape
    processed_class_map = process_class_map(class_map)
    video_annotations = []
    if mode == "instances":  # For each instance produce a video annotation
        for class_name, class_idxs in processed_class_map.items():
            if class_name == "background":
                continue
            class_img = np.isin(img, class_idxs).astype(np.uint8)
            cc_img, num_labels = cc3d.connected_components(class_img, return_N=True)
            for instance_id in range(1, num_labels):
                video_annotation = get_video_annotation(cc_img, class_idxs=[instance_id], class_name=class_name)
                if video_annotation:
                    video_annotations.append(video_annotation)
    elif mode == "image":  # For each frame and each class produce a single frame video annotation
        for i in range(shape[-1]):
            slice_mask = img[:, :, i].astype(np.uint8)
            for class_name, class_idxs in processed_class_map.items():
                frame_annotations = {}
                if class_name == "background":
                    continue
                class_mask = np.isin(slice_mask, class_idxs).astype(np.uint8).copy()
                polygon = mask_to_polygon(mask=class_mask, class_name=class_name)
                if polygon is None:
                    continue
                frame_annotations[i] = polygon
                video_annotation = dt.make_video_annotation(
                    frame_annotations,
                    keyframes={i: True, i + 1: True},
                    segments=[[i, i + 1]],
                    interpolated=False,
                    slot_names=[],
                )
                video_annotations.append(video_annotation)
    elif mode == "video":  # For each class produce a single video annotation
        for class_name, class_idxs in processed_class_map.items():
            if class_name == "background":
                continue
            video_annotation = get_video_annotation(img, class_idxs=class_idxs, class_name=class_name)
            if video_annotation is None:
                continue
            video_annotations.append(video_annotation)
    annotation_classes = set(
        [dt.AnnotationClass(class_name, "polygon", "polygon") for class_name in class_map.values()]
    )
    return dt.AnnotationFile(
        path=json_path,
        filename=str(filename),
        remote_path="/",
        annotation_classes=annotation_classes,
        annotations=video_annotations,
        slots=[dt.Slot(name=None, type="dicom", source_files=[{"url": None, "file_name": str(filename)}])],
    )


def get_video_annotation(volume: np.ndarray, class_name: str, class_idxs: List[int]) -> Optional[dt.VideoAnnotation]:
    frame_annotations = OrderedDict()
    for i in range(volume.shape[-1]):
        slice_mask = volume[:, :, i].astype(np.uint8)
        class_mask = np.isin(slice_mask, class_idxs).astype(np.uint8).copy()
        if class_mask.sum() == 0:
            continue

        polygon = mask_to_polygon(mask=class_mask, class_name=class_name)
        if polygon is None:
            continue
        frame_annotations[i] = polygon
    all_frame_ids = list(frame_annotations.keys())
    if not all_frame_ids:
        return None
    if len(all_frame_ids) == 1:
        segments = [[all_frame_ids[0], all_frame_ids[0] + 1]]
    elif len(all_frame_ids) > 1:
        segments = [[min(all_frame_ids), max(all_frame_ids)]]
    video_annotation = dt.make_video_annotation(
        frame_annotations,
        keyframes={f_id: True for f_id in all_frame_ids},
        segments=segments,
        interpolated=False,
        slot_names=[],
    )
    return video_annotation


def mask_to_polygon(mask: np.ndarray, class_name: str) -> Optional[dt.Annotation]:
    _labels, external_paths, _internal_paths = find_contours(mask)
    # annotations = []
    if len(external_paths) > 1:
        paths = []
        for external_path in external_paths:
            # skip paths with less than 2 points
            if len(external_path) // 2 <= 2:
                continue
            path = [{"x": y, "y": x} for x, y in zip(external_path[0::2], external_path[1::2])]
            paths.append(path)
        if len(paths) > 1:
            polygon = dt.make_complex_polygon(class_name, paths)
        elif len(paths) == 1:
            polygon = dt.make_polygon(
                class_name,
                point_path=paths[0],
            )
        else:
            return None
    elif len(external_paths) == 1:
        external_path = external_paths[0]
        if len(external_path) < 6:
            return None
        polygon = dt.make_polygon(
            class_name,
            point_path=[{"x": y, "y": x} for x, y in zip(external_path[0::2], external_path[1::2])],
        )
    else:
        return None
    return polygon


def process_class_map(class_map):
    """
    This function takes a class_map and returns a dictionary with the class names as keys and
    all the corresponding class indexes as values.
    """
    processed_class_map = defaultdict(list)
    for key, value in class_map.items():
        processed_class_map[value].append(int(key))
    return processed_class_map


def rectify_header_sform_qform(img_nii):
    """
    Look at the sform and qform of the nifti object and correct it if any
    incompatibilities with pixel dimensions

    Adapted from https://github.com/NifTK/NiftyNet/blob/v0.6.0/niftynet/io/misc_io.py

    Args:
        img_nii: nifti image object
    """
    d = img_nii.header["dim"][0]
    pixdim = np.asarray(img_nii.header.get_zooms())[:d]
    sform, qform = img_nii.get_sform(), img_nii.get_qform()
    norm_sform = affine_to_spacing(sform, r=d)
    norm_qform = affine_to_spacing(qform, r=d)
    sform_mismatch = not np.allclose(norm_sform, pixdim)
    qform_mismatch = not np.allclose(norm_qform, pixdim)

    if img_nii.header["sform_code"] != 0:
        if not sform_mismatch:
            return img_nii
        if not qform_mismatch:
            img_nii.set_sform(img_nii.get_qform())
            return img_nii
    if img_nii.header["qform_code"] != 0:
        if not qform_mismatch:
            return img_nii
        if not sform_mismatch:
            img_nii.set_qform(img_nii.get_sform())
            return img_nii

    norm = affine_to_spacing(img_nii.affine, r=d)
    warnings.warn(f"Modifying image pixdim from {pixdim} to {norm}")

    img_nii.header.set_zooms(norm)
    return img_nii


def affine_to_spacing(affine: np.ndarray, r: int = 3, dtype=float, suppress_zeros: bool = True) -> np.ndarray:
    """
    Copied over from monai.data.utils - https://docs.monai.io/en/stable/_modules/monai/data/utils.html

    Computing the current spacing from the affine matrix.

    Args:
        affine: a d x d affine matrix.
        r: indexing based on the spatial rank, spacing is computed from `affine[:r, :r]`.
        dtype: data type of the output.
        suppress_zeros: whether to surpress the zeros with ones.

    Returns:
        an `r` dimensional vector of spacing.
    """
    spacing = np.sqrt(np.sum(affine[:r, :r] * affine[:r, :r], axis=0))
    if suppress_zeros:
        spacing[spacing == 0] = 1.0
    return spacing


def correct_nifti_header_if_necessary(img_nii):
    """
    Check nifti object header's format, update the header if needed.
    In the updated image pixdim matches the affine.

    Args:
        img_nii: nifti image object
    """
    if img_nii.header.get("dim") is None:
        return img_nii  # not nifti?
    dim = img_nii.header["dim"][0]
    if dim >= 5:
        return img_nii  # do nothing for high-dimensional array
    # check that affine matches zooms
    pixdim = np.asarray(img_nii.header.get_zooms())[:dim]
    norm_affine = affine_to_spacing(img_nii.affine, r=dim)
    if np.allclose(pixdim, norm_affine):
        return img_nii
    if hasattr(img_nii, "get_sform"):
        return rectify_header_sform_qform(img_nii)
    return img_nii


def process_nifti(input_data: Union[Sequence[nib.nifti1.Nifti1Image], nib.nifti1.Nifti1Image]):
    """
    Function which takes in a single nifti path or a list of nifti paths
    and returns the pixel_array, affine and pixdim
    """
    if isinstance(input_data, nib.nifti1.Nifti1Image):
        img = correct_nifti_header_if_necessary(input_data)
        img = nib.funcs.as_closest_canonical(img)
        axcodes = nib.orientations.aff2axcodes(img.affine)
        # TODO: Future feature to pass custom ornt could go here.
        ornt = [[0.0, -1.0], [1.0, -1.0], [1.0, -1.0]]
        data_array = nib.orientations.apply_orientation(img.get_fdata(), ornt)
        return data_array
