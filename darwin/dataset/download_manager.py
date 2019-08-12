import json
import time
from pathlib import Path
from typing import Optional

import requests

from darwin.utils import urljoin


def download_all_images_from_annotations(
    api_url: str, annotations_path: Path, images_path: str, annotation_format="json"
):
    """Helper function: downloads an image given a .json annotation path. """
    Path(images_path).mkdir(exist_ok=True)

    if annotation_format not in ["json", "xml"]:
        print(f"Annotation format {annotation_format} not supported")
        return

    # return both the count and a generator for doing the actual downloads
    count = sum(1 for _ in annotations_path.glob(f"*.{annotation_format}"))
    generator = lambda: (
        download_image_from_annotation(
            api_url, annotation_path, images_path, annotation_format
        )
        for annotation_path in annotations_path.glob(f"*.{annotation_format}")
    )
    return generator, count


def download_image_from_annotation(
    api_url: str, annotation_path: Path, images_path: str, annotation_format: str
):
    """Helper function: downloads the all images corresponsing to a project. """
    if annotation_format == "json":
        download_image_from_json_annotation(api_url, annotation_path, images_path)
    elif annotation_format == "xml":
        print("sorry can't let you do that dave")
        # TODO: fix me
        # download_image_from_xml_annotation(annotation_path, images_path)


def download_image_from_json_annotation(api_url: str, annotation_path: Path, images_path: str):
    """Helper function: downloads an image given a .json annotation path. """
    Path(images_path).mkdir(exist_ok=True)
    with open(annotation_path, "r") as file:
        parsed = json.loads(file.read())
        path = Path(images_path) / f"{annotation_path.stem}.png"
        download_image(urljoin(api_url.replace("api/", ""), parsed["image"]["url"]), path)


def download_image(url: str, path: Path, verbose: Optional[bool] = False):
    """Helper function: downloads one image from url. """
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
            with open(path, "wb") as file:
                for chunk in response:
                    file.write(chunk)
            return
        # Fatal-error status: fail
        if 400 <= response.status_code <= 499:
            raise Exception(response.status_code, response.json())
        # Timeout
        if time.time() -  start > TIMEOUT:
            raise Exception(f"Timeout url request ({url}) after {TIMEOUT} seconds.")