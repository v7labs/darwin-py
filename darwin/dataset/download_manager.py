"""
Holds helper functions that deal with downloading videos and images.
"""

import functools
import os
import time
import urllib
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import numpy as np
import orjson as json
import requests
from PIL import Image
from requests.adapters import HTTPAdapter, Retry
from rich.console import Console

import darwin.datatypes as dt
from darwin.dataset.utils import sanitize_filename
from darwin.datatypes import AnnotationFile
from darwin.exceptions import MissingDependency
from darwin.utils import (
    attempt_decode,
    get_response_content,
    has_json_content_type,
    is_file_extension_allowed,
    parse_darwin_json,
)


def download_all_images_from_annotations(
    api_key: str,
    annotations_path: Path,
    images_path: Path,
    force_replace: bool = False,
    remove_extra: bool = False,
    annotation_format: str = "json",
    use_folders: bool = True,
    video_frames: bool = False,
    force_slots: bool = False,
    ignore_slots: bool = False,
) -> Tuple[Callable[[], Iterable[Any]], int]:
    """
    Downloads the all images corresponding to a project.

    Parameters
    ----------
    api_key : str
        API Key of the current team
    annotations_path : Path
        Path where the annotations are located
    images_path : Path
        Path where to download the images
    force_replace : bool, default: False
        Forces the re-download of an existing image
    remove_extra : bool, default: False
        Removes local files that would not be overwritten by the release being pulled.
    annotation_format : str, default: "json"
        Format of the annotations. Currently only JSON and xml are expected
    use_folders : bool, default: False
        Recreate folders
    video_frames : bool, default: False
        Pulls video frames images instead of video files
    force_slots: bool, default: False
        Pulls all slots of items into deeper file structure ({prefix}/{item_name}/{slot_name}/{file_name})
        If False, all multi-slotted items and items with slots containing multiple source files will be downloaded as the deeper file structure

    Returns
    -------
    generator : function
        Generator for doing the actual downloads
    count : int
        The files count

    Raises
    ------
    ValueError
        If the given annotation file is not in darwin (json) or pascalvoc (xml) format.
    """
    Path(images_path).mkdir(exist_ok=True)
    if annotation_format not in ["json", "xml"]:
        raise ValueError(f"Annotation format {annotation_format} not supported")

    # Verify that there is not already image in the images folder
    existing_images = {
        image
        for image in images_path.rglob("*")
        if is_file_extension_allowed(image.name)
    }

    annotations_to_download_path: List = []
    for annotation_path in annotations_path.glob(f"*.{annotation_format}"):
        annotation = parse_darwin_json(annotation_path, count=0)
        if annotation is None:
            continue

        if not force_replace:
            # Check the planned path for the image against the existing images
            planned_image_paths = _get_planned_image_paths(
                annotation, images_path, use_folders
            )

            if all(
                planned_image_path in existing_images
                for planned_image_path in planned_image_paths
            ):
                continue

        if force_slots:
            force_slots_for_item = True
        else:
            force_slots_for_item = len(annotation.slots) > 1 or any(
                len(slot.source_files) > 1 for slot in annotation.slots
            )

        annotations_to_download_path.append((annotation_path, force_slots_for_item))

    if remove_extra:
        annotations = (
            parse_darwin_json(annotation_path)
            for annotation_path in annotations_path.glob(f"*.{annotation_format}")
        )
        release_image_paths = [
            _get_planned_image_paths(annotation, images_path, use_folders)
            for annotation in annotations
        ]
        if any(isinstance(i, list) for i in release_image_paths):
            release_image_paths = [
                item for sublist in release_image_paths for item in sublist
            ]
        for existing_image in existing_images:
            if existing_image not in release_image_paths:
                print(f"Removing {existing_image} as it is not part of this release")
                existing_image.unlink()

        _remove_empty_directories(images_path)

    # Create the generator with the partial functions
    download_functions: List = []
    for annotation_path, force_slots in annotations_to_download_path:
        file_download_functions = lazy_download_image_from_annotation(
            api_key,
            annotation_path,
            images_path,
            annotation_format,
            use_folders,
            video_frames,
            force_slots,
            ignore_slots,
        )
        download_functions.extend(file_download_functions)

    if not use_folders:
        _check_for_duplicate_local_filepaths(download_functions)

    return lambda: download_functions, len(download_functions)


def lazy_download_image_from_annotation(
    api_key: str,
    annotation_path: Path,
    images_path: Path,
    annotation_format: str,
    use_folders: bool,
    video_frames: bool,
    force_slots: bool,
    ignore_slots: bool = False,
) -> Iterable[Callable[[], None]]:
    """
    Returns functions to download an image given an annotation. Same as `download_image_from_annotation`
    but returns Callables that trigger the download instead fetching files interally.

    Parameters
    ----------
    api_key : str
        API Key of the current team
    annotation_path : Path
        Path where the annotation is located
    images_path : Path
        Path where to download the image
    annotation_format : str
        Format of the annotations. Currently only JSON is supported
    use_folders : bool
        Recreate folder structure
    video_frames : bool
        Pulls video frames images instead of video files
    force_slots: bool
        Pulls all slots of items into deeper file structure ({prefix}/{item_name}/{slot_name}/{file_name})

    Raises
    ------
    NotImplementedError
        If the format of the annotation is not supported.
    """

    if annotation_format == "json":
        return _download_image_from_json_annotation(
            api_key,
            annotation_path,
            images_path,
            use_folders,
            video_frames,
            force_slots,
            ignore_slots,
        )
    else:
        console = Console()
        console.print("[bold red]Unsupported file format. Please use 'json'.")
        raise NotImplementedError


def _download_image_from_json_annotation(
    api_key: str,
    annotation_path: Path,
    image_path: Path,
    use_folders: bool,
    video_frames: bool,
    force_slots: bool,
    ignore_slots: bool = False,
) -> Iterable[Callable[[], None]]:
    annotation = parse_darwin_json(annotation_path, count=0)
    if annotation is None:
        return []

    # If we are using folders, extract the path for the image and create the folder if needed
    sub_path = annotation.remote_path if use_folders else Path("/")
    parent_path = Path(image_path) / Path(sub_path).relative_to(Path(sub_path).anchor)
    parent_path.mkdir(exist_ok=True, parents=True)

    annotation.slots.sort(key=lambda slot: slot.name or "0")
    if len(annotation.slots) > 0:
        if ignore_slots:
            return _download_single_slot_from_json_annotation(
                annotation,
                api_key,
                parent_path,
                annotation_path,
                video_frames,
                use_folders,
            )
        if force_slots:
            return _download_all_slots_from_json_annotation(
                annotation, api_key, parent_path, video_frames
            )
        else:
            return _download_single_slot_from_json_annotation(
                annotation,
                api_key,
                parent_path,
                annotation_path,
                video_frames,
                use_folders,
            )

    return []


def _download_all_slots_from_json_annotation(
    annotation: dt.AnnotationFile, api_key: str, parent_path: Path, video_frames: bool
) -> Iterable[Callable[[], None]]:
    generator = []
    for slot in annotation.slots:
        if not slot.name:
            raise ValueError("Slot name is required to download all slots")
        slot_path = (
            parent_path
            / sanitize_filename(annotation.filename)
            / sanitize_filename(slot.name)
        )
        slot_path.mkdir(exist_ok=True, parents=True)

        if video_frames and slot.type != "image":
            video_path: Path = slot_path
            video_path.mkdir(exist_ok=True, parents=True)
            if not slot.frame_urls:
                segment_manifests = get_segment_manifests(slot, slot_path, api_key)
                for index, manifest in enumerate(segment_manifests):
                    if slot.segments is None:
                        raise ValueError("No segments found")
                    segment_url = slot.segments[index]["url"]
                    path = video_path / f".{index:07d}.ts"
                    generator.append(
                        functools.partial(
                            _download_and_extract_video_segment,
                            segment_url,
                            api_key,
                            path,
                            manifest,
                        )
                    )
            else:
                for i, frame_url in enumerate(slot.frame_urls or []):
                    path = video_path / f"{i:07d}.png"
                    generator.append(
                        functools.partial(
                            _download_image, frame_url, path, api_key, slot
                        )
                    )
        else:
            for upload in slot.source_files:
                file_path = slot_path / sanitize_filename(upload["file_name"])
                generator.append(
                    functools.partial(
                        _download_image_with_trace,
                        annotation,
                        upload["url"],
                        file_path,
                        api_key,
                    )
                )
    return generator


def _download_single_slot_from_json_annotation(
    annotation: dt.AnnotationFile,
    api_key: str,
    parent_path: Path,
    annotation_path: Path,
    video_frames: bool,
    use_folders: bool = True,
) -> Iterable[Callable[[], None]]:
    slot = annotation.slots[0]
    generator = []

    if video_frames and slot.type != "image":
        video_path: Path = parent_path / (
            annotation_path.stem if not use_folders else Path(annotation.filename).stem
        )
        video_path.mkdir(exist_ok=True, parents=True)

        # Indicates it's a long video and uses the segment and manifest
        if not slot.frame_urls:
            segment_manifests = get_segment_manifests(slot, video_path, api_key)
            for index, manifest in enumerate(segment_manifests):
                if slot.segments is None:
                    raise ValueError("No segments found")
                segment_url = slot.segments[index]["url"]
                path = video_path / f".{index:07d}.ts"
                generator.append(
                    functools.partial(
                        _download_and_extract_video_segment,
                        segment_url,
                        api_key,
                        path,
                        manifest,
                    )
                )
        else:
            for i, frame_url in enumerate(slot.frame_urls):
                path = video_path / f"{i:07d}.png"
                generator.append(
                    functools.partial(_download_image, frame_url, path, api_key, slot)
                )
    else:
        if len(slot.source_files) > 0:
            image = slot.source_files[0]
            image_url = image["url"]
            image_filename = image["file_name"]
            if image_filename.endswith(".nii.gz"):
                suffix = ".nii.gz"
                stem = annotation.filename[: -len(suffix)]
            else:
                suffix = Path(image_filename).suffix
                stem = Path(annotation.filename).stem
            filename = str(Path(stem + suffix))
            image_path = parent_path / sanitize_filename(
                filename or annotation.filename
            )

            generator.append(
                functools.partial(
                    _download_image_with_trace,
                    annotation,
                    image_url,
                    image_path,
                    api_key,
                )
            )
    return generator


def _update_local_path(annotation: AnnotationFile, url, local_path):
    if annotation.version.major == 1:
        return

    # we modify raw json, as internal representation does't store all the data
    raw_annotation = attempt_decode(annotation.path)

    for slot in raw_annotation["item"]["slots"]:
        for source_file in slot["source_files"]:
            if source_file["url"] == url:
                source_file["local_path"] = str(local_path)

    with annotation.path.open(mode="w") as file:
        op = json.dumps(raw_annotation, json.OPT_INDENT_2).decode("utf-8")
        file.write(op)


def _download_image(
    url: str, path: Path, api_key: str, slot: Optional[dt.Slot] = None
) -> None:
    if path.exists():
        return
    TIMEOUT: int = 60
    start: float = time.time()

    transform_file_function = None
    if slot and slot.metadata and slot.metadata.get("colorspace") == "RG16":
        transform_file_function = _rg16_to_grayscale
    while True:
        if "token" in url:
            response: requests.Response = requests.get(url, stream=True)
        else:
            response = requests.get(
                url, headers={"Authorization": f"ApiKey {api_key}"}, stream=True
            )
        # Correct status: download image
        if response.ok and has_json_content_type(response):
            # this branch is a workaround for edge case in V1 when video file from external storage could be registered
            # with multiple keys (so that one file consist of several other)
            _fetch_multiple_files(path, response, transform_file_function)
            return
        elif response.ok:
            _write_file(path, response, transform_file_function)
            return
        # Fatal-error status: fail
        if 400 <= response.status_code <= 499:
            raise Exception(
                f"Request to ({url}) failed. Status code: {response.status_code}, content:\n{get_response_content(response)}."
            )
        # Timeout
        if time.time() - start > TIMEOUT:
            raise Exception(f"Timeout url request ({url}) after {TIMEOUT} seconds.")
        time.sleep(1)


def _download_image_with_trace(annotation, image_url, image_path, api_key):
    _download_image(image_url, image_path, api_key)
    _update_local_path(annotation, image_url, image_path)


def _fetch_multiple_files(
    path: Path, response: requests.Response, transform_file_function=None
) -> None:
    obj = response.json()
    if "urls" not in obj:
        raise Exception(f"Malformed response: {obj}")
    urls = obj["urls"]
    # remove extension from os file path, e.g /some/path/example.dcm -> /some/path/example
    # and create such directory
    dir_path = Path(path).with_suffix("")
    dir_path.mkdir(exist_ok=True, parents=True)
    for url in urls:
        # get filename which is last http path segment
        filename = urllib.parse.urlparse(url).path.rsplit("/", 1)[-1]
        path = dir_path / filename
        response = requests.get(url, stream=True)
        if response.ok:
            _write_file(path, response, transform_file_function)
        else:
            raise Exception(
                f"Request to ({url}) failed. Status code: {response.status_code}, content:\n{get_response_content(response)}."
            )


def _write_file(
    path: Path, response: requests.Response, transform_file_function=None
) -> None:
    with open(str(path), "wb") as file:
        for chunk in response:
            file.write(chunk)
    if transform_file_function is not None:
        transform_file_function(path)


def _rg16_to_grayscale(path):
    # Custom 16bit grayscale encoded on (RG)B channels
    # into regular 8bit grayscale

    image = Image.open(path)
    image_2d_rgb = np.asarray(image)

    image_2d_r = np.uint16(image_2d_rgb[:, :, 0]) << 8
    image_2d_g = np.uint16(image_2d_rgb[:, :, 1])

    image_2d_gray = np.bitwise_or(image_2d_r, image_2d_g)
    image_2d_gray = image_2d_gray / (1 << 16) * 255

    new_image = Image.fromarray(np.uint8(image_2d_gray), mode="L")
    new_image.save(path)


def _download_and_extract_video_segment(
    url: str, api_key: str, path: Path, manifest: dt.SegmentManifest
) -> None:
    _download_video_segment_file(url, api_key, path)
    _extract_frames_from_segment(path, manifest)
    path.unlink()


def _extract_frames_from_segment(path: Path, manifest: dt.SegmentManifest) -> None:
    # import cv2 here to avoid dependency on OpenCV when not needed if not installed as optional extra
    try:
        from cv2 import VideoCapture, imwrite  # pylint: disable=import-outside-toplevel
    except ImportError as e:
        raise MissingDependency(
            "Missing Dependency: OpenCV required for Video Extraction. Install with `pip install darwin-py\[ocv]`"
        ) from e
    cap = VideoCapture(str(path))

    # Read and save frames. Iterates over every frame because frame seeking in OCV is not reliable or guaranteed.
    frames_to_extract = {
        item.frame: item.visible_frame for item in manifest.items if item.visibility
    }
    frame_index = 0
    while cap.isOpened():
        success, frame = cap.read()
        if frame is None:
            break
        if not success:
            raise ValueError(
                f"Failed to read frame {frame_index} from video segment {path}"
            )
        if frame_index in frames_to_extract:
            visible_frame = frames_to_extract.pop(frame_index)
            frame_path = path.parent / f"{visible_frame:07d}.png"
            imwrite(str(frame_path), frame)
            if not frames_to_extract:
                break
        frame_index += 1
    cap.release()


def _download_video_segment_file(url: str, api_key: str, path: Path) -> None:
    with requests.Session() as session:
        retries = Retry(
            total=5, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504]
        )
        session.mount("https://", HTTPAdapter(max_retries=retries))
        if "token" in url:
            response = session.get(url)
        else:
            session.headers = {"Authorization": f"ApiKey {api_key}"}
            response = session.get(url)
    if not response.ok or (400 <= response.status_code <= 499):
        raise Exception(
            f"Request to ({url}) failed. Status code: {response.status_code}, content:\n{get_response_content(response)}."
        )
    # create new filename for segment with .
    with open(str(path), "wb") as file:
        for chunk in response:
            file.write(chunk)


def download_manifest_txts(urls: List[str], api_key: str, folder: Path) -> List[Path]:
    paths = []
    with requests.Session() as session:
        retries = Retry(
            total=5, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504]
        )
        session.mount("https://", HTTPAdapter(max_retries=retries))
        for index, url in enumerate(urls):
            if "token" in url:
                response = session.get(url)
            else:
                session.headers = {"Authorization": f"ApiKey {api_key}"}
                response = session.get(url)
            if not response.ok or (400 <= response.status_code <= 499):
                raise Exception(
                    f"Request to ({url}) failed. Status code: {response.status_code}, content:\n{get_response_content(response)}."
                )
            if not response.content:
                raise Exception(f"Manifest file ({url}) is empty.")
            path = folder / f"manifest_{index + 1}.txt"
            with open(str(path), "wb") as file:
                file.write(response.content)
            paths.append(path)
    return paths


def get_segment_manifests(
    slot: dt.Slot, parent_path: Path, api_key: str
) -> List[dt.SegmentManifest]:
    with TemporaryDirectory(dir=parent_path) as tmpdirname:
        tmpdir = Path(tmpdirname)
        if slot.frame_manifest is None:
            raise ValueError("No frame manifest found")
        frame_urls = [item["url"] for item in slot.frame_manifest]
        manifest_paths = download_manifest_txts(frame_urls, api_key, tmpdir)
        segment_manifests = _parse_manifests(manifest_paths, slot.name or "0")
    return segment_manifests


def _parse_manifests(paths: List[Path], slot: str) -> List[dt.SegmentManifest]:
    all_manifests: Dict[int, List[dt.ManifestItem]] = {}
    visible_frame_index = 0
    for path in paths:
        with open(path) as infile:
            for line in infile:
                frame, segment_str, visibility, timestamp = line.strip("\n").split(":")
                segment_int = int(segment_str)
                if segment_int not in all_manifests:
                    all_manifests[segment_int] = []
                if bool(int(visibility)):
                    all_manifests[segment_int].append(
                        dt.ManifestItem(
                            int(frame),
                            None,
                            segment_int,
                            True,
                            float(timestamp),
                            visible_frame_index,
                        )
                    )
                    visible_frame_index += 1
                else:
                    all_manifests[segment_int].append(
                        dt.ManifestItem(
                            int(frame), None, segment_int, False, float(timestamp), None
                        )
                    )
    # Create a list of segments, sorted by segment number and all items sorted by frame number
    segments = []
    for segment_int, seg_manifests in all_manifests.items():
        seg_manifests.sort(key=lambda x: x.frame)
        segments.append(
            dt.SegmentManifest(
                slot=slot,
                segment=segment_int,
                total_frames=len(seg_manifests),
                items=seg_manifests,
            )
        )

    # Calculate the absolute frame number for each item, as manifests are per segment
    absolute_frame = 0
    for segment in segments:
        for item in segment.items:
            item.absolute_frame = absolute_frame
            absolute_frame += 1
    return segments


def _get_planned_image_paths(
    annotation: dt.AnnotationFile, images_path: Path, use_folders: bool
) -> List[Path]:
    """
    Returns the local path that a dataset file will be downloaded to as part of a release.

    For multi-slotted items, returns one path for each slot.

    Parameters
    ----------
    annotation : AnnotationFile
        Annotation file corresponding to the dataset file
    images_path : Path
        Local directory where the dataset files will be downloaded to
    use_folders : bool
        Whether to recreate the remote folder structure locally for this release
    """
    file_paths = []
    filename = Path(annotation.filename)
    if len(annotation.slots) == 1 and len(annotation.slots[0].source_files) == 1:
        if use_folders and annotation.remote_path != "/":
            return [images_path / Path(annotation.remote_path.lstrip("/\\")) / filename]
        else:
            return [images_path / filename]
    else:
        for slot in annotation.slots:
            slot_name = Path(slot.name)
            for source_file in slot.source_files:
                file_name = source_file.file_name
                if use_folders and annotation.remote_path != "/":
                    file_paths.append(
                        images_path
                        / Path(annotation.remote_path.lstrip("/\\"))
                        / filename
                        / slot_name
                        / file_name
                    )
                else:
                    file_paths.append(images_path / filename / slot_name / file_name)
    return file_paths


def _remove_empty_directories(images_path: Path) -> bool:
    """
    Recursively removes empty directories in the given path

    Parameters
    ----------
    images_path : Path
        Path to remove empty subdirectories from
    """
    entries = os.listdir(images_path)
    is_empty = True

    for entry in entries:
        full_path = Path(os.path.join(images_path, entry))
        if os.path.isdir(full_path):
            if not _remove_empty_directories(full_path):
                is_empty = False
        else:
            if entry == ".DS_Store":
                os.remove(full_path)
                print(f"Removed file: {full_path}")
            else:
                is_empty = False

    # If the directory is empty files, remove it
    if is_empty and images_path != images_path.parent:
        os.rmdir(images_path)
        print(f"Removed empty directory: {images_path}")


def _check_for_duplicate_local_filepaths(
    download_functions: List[Callable[[], None]]
) -> None:
    """
    If pulling a release without folders, check for duplicate filepaths in the download functions.
    This can arise when pulling a flat release with identically named dataset items in different folders.

    If duplicates are found, display a warning message but do not block the download.

    Parameters
    ----------
    download_functions : List[Callable[[], None]]
        A list of download functions. Each one is responsible for downloading a single file.
    """
    image_paths_to_download = [
        download_function.args[2] for download_function in download_functions
    ]

    path_counts = Counter(image_paths_to_download)
    duplicate_download_paths = {
        path: count for path, count in path_counts.items() if count > 1
    }
    if duplicate_download_paths:
        console = Console()
        console.print(
            "[bold yellow]Warning: Identical filenames detected in your export release. \n\nYou are pulling a flat release with identically named dataset items.\nThe release will still be pulled, but to prevent overwriting your dataset files, please re-pull the release with the folder structure. This can be done as follows:[/bold yellow]"
        )
        console.print(
            "[bold yellow]- CLI: darwin dataset pull team_slug/dataset_slug --folders\n- SDK: dataset.pull(use_folders=True)[/bold yellow]\n"
        )
        console.print("[bold yellow]The following paths are duplicated:[/bold yellow]")
        for path, count in duplicate_download_paths.items():
            console.print(
                f"[bold yellow]- {path} is duplicated {count} times[/bold yellow]"
            )
