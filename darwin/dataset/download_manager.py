"""
Holds helper functions that deal with downloading videos and images.
"""

import functools
import time
import urllib
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional, Tuple

import deprecation
import numpy as np
import orjson as json
import requests
from PIL import Image
from rich.console import Console

import darwin.datatypes as dt
from darwin.dataset.utils import sanitize_filename
from darwin.datatypes import AnnotationFile
from darwin.utils import (
    get_response_content,
    has_json_content_type,
    is_image_extension_allowed,
    parse_darwin_json,
)
from darwin.version import __version__


@deprecation.deprecated(
    deprecated_in="0.7.5",
    removed_in="0.8.0",
    current_version=__version__,
    details="The api_url parameter will be removed.",
)
def download_all_images_from_annotations(
    api_key: str,
    api_url: str,
    annotations_path: Path,
    images_path: Path,
    force_replace: bool = False,
    remove_extra: bool = False,
    annotation_format: str = "json",
    use_folders: bool = False,
    video_frames: bool = False,
    force_slots: bool = False,
) -> Tuple[Callable[[], Iterable[Any]], int]:
    """
    Downloads the all images corresponding to a project.

    Parameters
    ----------
    api_key : str
        API Key of the current team
    api_url : str
        Url of the darwin API (e.g. 'https://darwin.v7labs.com/api/')
    annotations_path : Path
        Path where the annotations are located
    images_path : Path
        Path where to download the images
    force_replace : bool, default: False
        Forces the re-download of an existing image
    remove_extra : bool, default: False
        Removes existing images for which there is not corresponding annotation
    annotation_format : str, default: "json"
        Format of the annotations. Currently only JSON and xml are expected
    use_folders : bool, default: False
        Recreate folders
    video_frames : bool, default: False
        Pulls video frames images instead of video files
    force_slots: bool
        Pulls all slots of items into deeper file structure ({prefix}/{item_name}/{slot_name}/{file_name})

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
    unfiltered_files = images_path.rglob(f"*") if use_folders else images_path.glob(f"*")
    existing_images = {image.stem: image for image in unfiltered_files if is_image_extension_allowed(image.suffix)}

    annotations_to_download_path = []
    for annotation_path in annotations_path.glob(f"*.{annotation_format}"):
        annotation = parse_darwin_json(annotation_path, count=0)
        if annotation is None:
            continue

        if not force_replace:
            # Check collisions on image filename and json filename on the system
            if annotation.filename in existing_images:
                continue
            if sanitize_filename(annotation_path.stem) in existing_images:
                continue
        annotations_to_download_path.append(annotation_path)
        if len(annotation.slots) > 1:
            force_slots = True

        for slot in annotation.slots:
            if len(slot.source_files) > 1:
                force_slots = True

    if remove_extra:
        # Removes existing images for which there is not corresponding annotation
        annotations_downloaded_stem = [a.stem for a in annotations_path.glob(f"*.{annotation_format}")]
        for existing_image in existing_images.values():
            if existing_image.stem not in annotations_downloaded_stem:
                print(f"Removing {existing_image} as there is no corresponding annotation")
                existing_image.unlink()
    # Create the generator with the partial functions
    download_functions: List = []
    for annotation_path in annotations_to_download_path:
        file_download_functions = lazy_download_image_from_annotation(
            api_key,
            annotation_path,
            images_path,
            annotation_format,
            use_folders,
            video_frames,
            force_slots,
        )
        download_functions.extend(file_download_functions)

    return lambda: download_functions, len(download_functions)


@deprecation.deprecated(
    deprecated_in="0.7.5",
    removed_in="0.8.0",
    current_version=__version__,
    details="The api_url parameter will be removed.",
)
def download_image_from_annotation(
    api_key: str,
    api_url: str,
    annotation_path: Path,
    images_path: Path,
    annotation_format: str,
    use_folders: bool,
    video_frames: bool,
    force_slots: bool,
) -> None:
    """
    Dispatches functions to download an image given an annotation.

    Parameters
    ----------
    api_key : str
        API Key of the current team
    api_url : str
        Url of the darwin API (e.g. 'https://darwin.v7labs.com/api/')
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

    console = Console()

    if annotation_format == "json":
        downloadables = _download_image_from_json_annotation(
            api_key, annotation_path, images_path, use_folders, video_frames, force_slots
        )
        for downloadable in downloadables:
            downloadable()
    else:
        console.print("[bold red]Unsupported file format. Please use 'json'.")
        raise NotImplementedError


def lazy_download_image_from_annotation(
    api_key: str,
    annotation_path: Path,
    images_path: Path,
    annotation_format: str,
    use_folders: bool,
    video_frames: bool,
    force_slots: bool,
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

    console = Console()

    if annotation_format == "json":
        return _download_image_from_json_annotation(
            api_key, annotation_path, images_path, use_folders, video_frames, force_slots
        )
    else:
        console.print("[bold red]Unsupported file format. Please use 'json'.")
        raise NotImplementedError


def _download_image_from_json_annotation(
    api_key: str,
    annotation_path: Path,
    image_path: Path,
    use_folders: bool,
    video_frames: bool,
    force_slots: bool,
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
        if force_slots:
            return _download_all_slots_from_json_annotation(annotation, api_key, parent_path, video_frames)
        else:
            return _download_single_slot_from_json_annotation(
                annotation, api_key, parent_path, annotation_path, video_frames
            )

    return []


def _download_all_slots_from_json_annotation(annotation, api_key, parent_path, video_frames):
    generator = []
    for slot in annotation.slots:
        slot_path = parent_path / sanitize_filename(annotation.filename) / sanitize_filename(slot.name)
        slot_path.mkdir(exist_ok=True, parents=True)

        if video_frames and slot.type != "image":
            video_path: Path = slot_path / "sections"
            video_path.mkdir(exist_ok=True, parents=True)
            for i, frame_url in enumerate(slot.frame_urls or []):
                path = video_path / f"{i:07d}.png"
                generator.append(functools.partial(_download_image, frame_url, path, api_key, slot))
        else:
            for upload in slot.source_files:
                file_path = slot_path / sanitize_filename(upload["file_name"])
                generator.append(
                    functools.partial(_download_image_with_trace, annotation, upload["url"], file_path, api_key)
                )
    return generator


def _download_single_slot_from_json_annotation(annotation, api_key, parent_path, annotation_path, video_frames):
    slot = annotation.slots[0]
    generator = []

    if video_frames and slot.type != "image":
        video_path: Path = parent_path / annotation_path.stem
        video_path.mkdir(exist_ok=True, parents=True)
        for i, frame_url in enumerate(slot.frame_urls or []):
            path = video_path / f"{i:07d}.png"
            generator.append(functools.partial(_download_image, frame_url, path, api_key, slot))
    else:
        if len(slot.source_files) > 0:
            image_url = slot.source_files[0]["url"]
            filename = slot.source_files[0]["file_name"]
            image_path = parent_path / sanitize_filename(filename or annotation.filename)

            generator.append(functools.partial(_download_image_with_trace, annotation, image_url, image_path, api_key))
    return generator


def _update_local_path(annotation: AnnotationFile, url, local_path):

    if annotation.version.major == 1:
        return

    # we modify raw json, as internal representation does't store all the data
    with annotation.path.open() as file:
        raw_annotation = json.loads(file.read())

        for slot in raw_annotation["item"]["slots"]:
            for source_file in slot["source_files"]:
                if source_file["url"] == url:
                    source_file["local_path"] = str(local_path)

    with annotation.path.open(mode="w") as file:
        op = json.dumps(raw_annotation, json.OPT_INDENT_2).decode("utf-8")
        file.write(op)


@deprecation.deprecated(
    deprecated_in="0.7.5",
    removed_in="0.8.0",
    current_version=__version__,
    details="Use the ``download_image_from_annotation`` instead.",
)
def download_image_from_json_annotation(
    api_key: str, api_url: str, annotation_path: Path, image_path: Path, use_folders: bool, video_frames: bool
) -> None:
    """
    Downloads an image given a ``.json`` annotation path and renames the json after the image's
    filename.

    Parameters
    ----------
    api_key : str
        API Key of the current team
    api_url : str
        Url of the darwin API (e.g. 'https://darwin.v7labs.com/api/')
    annotation_path : Path
        Path where the annotation is located
    image_path : Path
        Path where to download the image
    use_folders : bool
        Recreate folders
    video_frames : bool
        Pulls video frames images instead of video files
    """
    with annotation_path.open() as file:
        annotation = json.loads(file.read())

    # If we are using folders, extract the path for the image and create the folder if needed
    sub_path = annotation["image"].get("path", "/") if use_folders else "/"
    parent_path = Path(image_path) / Path(sub_path).relative_to(Path(sub_path).anchor)
    parent_path.mkdir(exist_ok=True, parents=True)

    if video_frames and "frame_urls" in annotation["image"]:
        video_path: Path = parent_path / annotation_path.stem
        video_path.mkdir(exist_ok=True, parents=True)
        for i, frame_url in enumerate(annotation["image"]["frame_urls"]):
            path = video_path / f"{i:07d}.png"
            _download_image(frame_url, path, api_key)
    else:
        image_url = annotation["image"]["url"]
        image_path = parent_path / sanitize_filename(annotation["image"]["filename"])
        _download_image(image_url, image_path, api_key)


@deprecation.deprecated(
    deprecated_in="0.7.5",
    removed_in="0.8.0",
    current_version=__version__,
    details="Use the ``download_image_from_annotation`` instead.",
)
def download_image(url: str, path: Path, api_key: str) -> None:
    """
    Helper function: downloads one image from url.

    Parameters
    ----------
    url : str
        Url of the image to download
    path : Path
        Path where to download the image, with filename
    api_key : str
        API Key of the current team
    """
    if path.exists():
        return
    TIMEOUT: int = 60
    start: float = time.time()
    while True:
        if "token" in url:
            response: requests.Response = requests.get(url, stream=True)
        else:
            response = requests.get(url, headers={"Authorization": f"ApiKey {api_key}"}, stream=True)
        # Correct status: download image
        if response.ok:
            with open(str(path), "wb") as file:
                for chunk in response:
                    file.write(chunk)
            return
        # Fatal-error status: fail
        if 400 <= response.status_code <= 499:
            raise Exception(response.status_code, response.json())
        # Timeout
        if time.time() - start > TIMEOUT:
            raise Exception(f"Timeout url request ({url}) after {TIMEOUT} seconds.")
        time.sleep(1)


def _download_image(url: str, path: Path, api_key: str, slot: Optional[dt.Slot] = None) -> None:
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
            response = requests.get(url, headers={"Authorization": f"ApiKey {api_key}"}, stream=True)
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


def _fetch_multiple_files(path: Path, response: requests.Response, transform_file_function=None) -> None:
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


def _write_file(path: Path, response: requests.Response, transform_file_function=None) -> None:
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
