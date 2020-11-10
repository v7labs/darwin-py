import functools
import json
import time
from pathlib import Path

import requests

from darwin.utils import is_image_extension_allowed


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
):
    """Helper function: downloads the all images corresponding to a project.

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
    force_replace: bool
        Forces the re-download of an existing image
    remove_extra: bool
        Removes existing images for which there is not corresponding annotation
    annotation_format : str
        Format of the annotations. Currently only JSON and xml are expected
    use_folders: bool
        Recreate folders
    video_frames: bool
        Pulls video frames images instead of video files

    Returns
    -------
    generator : function
        Generator for doing the actual downloads,
    count : int
        The files count
    """
    Path(images_path).mkdir(exist_ok=True)
    if annotation_format not in ["json", "xml"]:
        raise ValueError(f"Annotation format {annotation_format} not supported")

    # Verify that there is not already image in the images folder
    unfiltered_files = images_path.rglob(f"*") if use_folders else images_path.glob(f"*")
    existing_images = {image.stem: image for image in unfiltered_files if is_image_extension_allowed(image.suffix)}

    annotations_to_download_path = []
    for annotation_path in annotations_path.glob(f"*.{annotation_format}"):
        annotation = json.load(annotation_path.open())
        if not force_replace:
            # Check collisions on image filename, original_filename and json filename on the system
            if Path(annotation["image"]["filename"]).stem in existing_images:
                continue
            if Path(annotation["image"]["original_filename"]).stem in existing_images:
                continue
            if annotation_path.stem in existing_images:
                continue
        annotations_to_download_path.append(annotation_path)

    if remove_extra:
        # Removes existing images for which there is not corresponding annotation
        annotations_downloaded_stem = [a.stem for a in annotations_path.glob(f"*.{annotation_format}")]
        for existing_image in existing_images.values():
            if existing_image.stem not in annotations_downloaded_stem:
                print(f"Removing {existing_image} as there is no corresponding annotation")
                existing_image.unlink()
    # Create the generator with the partial functions
    count = len(annotations_to_download_path)
    generator = lambda: (
        functools.partial(
            download_image_from_annotation,
            api_key,
            api_url,
            annotation_path,
            images_path,
            annotation_format,
            use_folders,
            video_frames,
        )
        for annotation_path in annotations_to_download_path
    )
    return generator, count


def download_image_from_annotation(
    api_key: str, api_url: str, annotation_path: Path, images_path: str, annotation_format: str, use_folders: bool, video_frames: bool
):
    """Helper function: dispatcher of functions to download an image given an annotation

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
    use_folders: bool
        Recreate folder structure
    video_frames: bool
        Pulls video frames images instead of video files
    """
    if annotation_format == "json":
        download_image_from_json_annotation(api_key, api_url, annotation_path, images_path, use_folders, video_frames)
    elif annotation_format == "xml":
        print("sorry can't let you do that dave")
        raise NotImplementedError
        # download_image_from_xml_annotation(annotation_path, images_path)


def download_image_from_json_annotation(
    api_key: str, api_url: str, annotation_path: Path, image_path: str, use_folders: bool, video_frames: bool
):
    """
    Helper function: downloads an image given a .json annotation path
    and renames the json after the image filename

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
    use_folders: bool
        Recreate folders
    video_frames: bool
        Pulls video frames images instead of video files
    """
    annotation = json.load(annotation_path.open())

    # If we are using folders, extract the path for the image and create the folder if needed
    sub_path = annotation["image"].get("path", "/") if use_folders else "/"
    parent_path = Path(image_path) / Path(sub_path).relative_to(Path(sub_path).anchor)
    parent_path.mkdir(exist_ok=True, parents=True)

    if video_frames and "frame_urls" in annotation["image"]:
        video_path = parent_path / annotation_path.stem
        video_path.mkdir(exist_ok=True, parents=True)
        for i, frame_url in enumerate(annotation["image"]["frame_urls"]):
            path = video_path / f"{i:07d}.jpg"
            download_image(frame_url, path, api_key)
    else:
        image_url = annotation["image"]["url"]
        image_path = parent_path / annotation["image"]["filename"]
        download_image(image_url, image_path, api_key)


def download_image(url: str, path: Path, api_key: str):
    """Helper function: downloads one image from url.

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
    TIMEOUT = 60
    start = time.time()
    while True:
        if "token" in url:
            response = requests.get(url, stream=True)
        else:
            response = requests.get(url, headers={"Authorization": f"ApiKey {api_key}"}, stream=True)
        # Correct status: download image
        if response.status_code == 200:
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
