import functools
import itertools
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from darwin.exceptions import UnsupportedFileType
from darwin.utils import SUPPORTED_IMAGE_EXTENSIONS, SUPPORTED_VIDEO_EXTENSIONS


def _split_on_file_type(files: List[str]):
    images = []
    videos = []
    for file_path in files:
        suffix = Path(file_path).suffix
        if suffix in SUPPORTED_IMAGE_EXTENSIONS:
            images.append(str(file_path))
        elif suffix in SUPPORTED_VIDEO_EXTENSIONS:
            videos.append(str(file_path))
        else:
            raise UnsupportedFileType(file_path)
    return images, videos


def add_files_to_dataset(
    client: "Client", dataset_id: str, filenames: List[Path], fps: int = 1
):
    """Helper function: upload images to an existing remote dataset

    Parameters
    ----------
    client : Client
        The client to use to communicate with the server
    dataset_id : str
        ID of the dataset to add the files to
    filenames : list[Path]
        List of filenames to upload
    fps : int
        Frame rate to split videos in.
    Returns
    -------

    """
    if not filenames:
        return

    for filenames_chunk in chunk(filenames, 100):
        images, videos = _split_on_file_type(filenames_chunk)
        data = client.put(
            f"/datasets/{dataset_id}",
            {
                "image_filenames": [Path(image).name for image in images],
                "videos": [{"fps": fps, "original_filename": Path(video).name} for video in videos],
            },
        )

        image_generator = lambda: (
            functools.partial(
                client.put,
                f"/dataset_images/{upload_file_to_s3(client, image_file, images)['id']}/confirm_upload",
                payload={},
            )
            for image_file in data["image_data"]
        )

        video_generator = lambda: (
            functools.partial(
                client.put,
                f"/dataset_videos/{upload_file_to_s3(client, video_file, videos)['id']}/confirm_upload",
                payload={},
            )
            for video_file in data["video_data"]
        )

        generator = itertools.chain(image_generator(), video_generator())

        return generator, len(filenames)


def chunk(items, size):
    """ Chunks paths in batches of size.
    No batch has any duplicates with regards to file name.
    This is needed due to a limitation in the upload api.
    """
    current_list = []
    current_names = set()
    left_over = []
    for item in items:
        name = Path(item).name
        if name in current_names:
            left_over.append(item)
        else:
            current_list.append(item)
            current_names.add(name)
        if len(current_list) >= size:
            yield current_list
            current_list = []
            current_names = set()
    if left_over:
        yield from chunk(left_over, size)
    if current_list:
        yield current_list


def upload_file_to_s3(
    client: "Client", file: Dict[str, Any], full_path: List[str]
) -> Dict[str, Any]:
    """Helper function: upload data to AWS S3"""
    key = file["key"]
    file_path = [path for path in full_path if Path(path).name == file["original_filename"]][0]
    image_id = file["id"]
    response = sign_upload(client, image_id, key, Path(file_path))
    signature = response["signature"]
    end_point = response["postEndpoint"]

    s3_response = upload_to_s3(signature, end_point, file_path)
    # if not str(s3_response.status_code).startswith("2"):
    #     process_response(s3_response)

    if s3_response.status_code == 400:
        print(f"Detail: Bad request when uploading to AWS S3 -- file: {file_path}")

    return {"key": key, "id": image_id}


def upload_to_s3(signature, end_point, file_path=None):
    """

    Parameters
    ----------
    signature
    end_point
    file_path

    Returns
    -------
    requests.Response
    Response of the post request
    """
    with open(file_path, "rb") as file:
        return requests.post("http:" + end_point, data=signature, files={"file": file})


def sign_upload(client, image_id, key, file_path):
    """

    Parameters
    ----------
    client
    image_id
    key
    file_path

    Returns
    -------

    """
    file_format = Path(file_path).suffix
    if file_format in SUPPORTED_IMAGE_EXTENSIONS:
        return client.post(
            f"/dataset_images/{image_id}/sign_upload?key={key}",
            payload={"filePath": str(file_path), "contentType": f"image/{file_format}"},
        )
    elif file_format in SUPPORTED_VIDEO_EXTENSIONS:
        return client.post(
            f"/dataset_videos/{image_id}/sign_upload?key={key}",
            payload={"filePath": str(file_path), "contentType": f"video/{file_format}"},
        )
