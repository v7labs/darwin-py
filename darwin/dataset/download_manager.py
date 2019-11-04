import functools
import json
import os
import time
from pathlib import Path
from typing import Optional

import requests

from darwin.utils import urljoin


def download_all_images_from_annotations(
    api_url: str, annotations_path: Path, images_path: Path, annotation_format: str = "json"
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
    annotation_format : str
        Format of the annotations. Currently only JSON and xml are expected

    Returns
    -------
    generator :
    function
        Generator for doing the actual downloads,
    count : int
        The files count
    """
    Path(images_path).mkdir(exist_ok=True)
    if annotation_format not in ["json", "xml"]:
        print(f"Annotation format {annotation_format} not supported")
        return
    count = sum(1 for _ in annotations_path.glob(f"*.{annotation_format}"))
    generator = lambda: (
        functools.partial(
            download_image_from_annotation, api_url, annotation_path, images_path, annotation_format
        )
        for annotation_path in annotations_path.glob(f"*.{annotation_format}")
    )
    return generator, count


def download_image_from_annotation(
    api_url: str, annotation_path: Path, images_path: str, annotation_format: str
):
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

    with open(str(annotation_path), "r") as file:
        parsed = json.loads(file.read())
        image_file_name = Path(parsed["image"]["filename"])
        path = Path(image_path) / image_file_name
        download_image(urljoin(api_url.replace("api/", ""), parsed["image"]["url"]), path)
    # Rename the current JSON file to match the image filename
    annotation_path.rename(annotation_path.parent / f"{image_file_name.stem}.json")


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
