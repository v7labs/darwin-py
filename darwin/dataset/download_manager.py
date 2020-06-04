import functools
import json
import time
from pathlib import Path
from typing import Optional

import requests

from darwin.utils import is_image_extension_allowed


def download_all_images_from_annotations(
    api_url: str,
    annotations_path: Path,
    images_path: Path,
    force_replace: bool = False,
    remove_extra: bool = False,
    annotation_format: str = "json",
):
    """Helper function: downloads the all images corresponding to a project.

    Parameters
    ----------
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
    existing_images = {
        image.stem: image for image in images_path.glob(f"*") if is_image_extension_allowed(image.suffix)
    }
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
        functools.partial(download_image_from_annotation, api_url, annotation_path, images_path, annotation_format)
        for annotation_path in annotations_to_download_path
    )
    return generator, count


def download_image_from_annotation(api_url: str, annotation_path: Path, images_path: str, annotation_format: str):
    """Helper function: dispatcher of functions to download an image given an annotation

    Parameters
    ----------
    api_url : str
        Url of the darwin API (e.g. 'https://darwin.v7labs.com/api/')
    annotation_path : Path
        Path where the annotation is located
    images_path : Path
        Path where to download the image
    annotation_format : str
        Format of the annotations. Currently only JSON is supported
    """
    if annotation_format == "json":
        download_image_from_json_annotation(api_url, annotation_path, images_path)
    elif annotation_format == "xml":
        print("sorry can't let you do that dave")
        raise NotImplementedError
        # download_image_from_xml_annotation(annotation_path, images_path)


def download_image_from_json_annotation(api_url: str, annotation_path: Path, image_path: str):
    """
    Helper function: downloads an image given a .json annotation path
    and renames the json after the image filename

    Parameters
    ----------
    api_url : str
        Url of the darwin API (e.g. 'https://darwin.v7labs.com/api/')
    annotation_path : Path
        Path where the annotation is located
    image_path : Path
        Path where to download the image
    """
    Path(image_path).mkdir(exist_ok=True)
    annotation = json.load(annotation_path.open())

    # Make the image file name match the one of the JSON annotation
    original_filename_suffix = Path(annotation["image"]["original_filename"]).suffix
    path = Path(image_path) / (annotation_path.stem + original_filename_suffix)

    download_image(annotation["image"]["url"], path)


def download_image(url: str, path: Path, verbose: Optional[bool] = False):
    """Helper function: downloads one image from url.

    Parameters
    ----------
    url : str
        Url of the image to download
    path : Path
        Path where to download the image, with filename
    verbose : bool
        Flag for the logging level
    """
    if path.exists():
        return
    if verbose:
        print(f"Dowloading {path.name}")
    TIMEOUT = 60
    start = time.time()
    while True:
        response = requests.get(url, stream=True)
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
