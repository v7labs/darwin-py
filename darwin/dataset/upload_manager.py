from pathlib import Path
from typing import TYPE_CHECKING, List

import requests

import darwin
from darwin.exceptions import UnsupportedFileType
from darwin.utils import SUPPORTED_IMAGE_EXTENSIONS, SUPPORTED_VIDEO_EXTENSIONS

if TYPE_CHECKING:
    from darwin.client import Client

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


def upload_file_to_s3(client: "Client", file: requests.Response) -> dict:
    """Helper function: upload data to AWS S3"""
    key = file["key"]
    file_path = file["original_filename"]
    image_id = file["id"]

    response = sign_upload(client, image_id, key, file_path)
    signature = response["signature"]
    end_point = response["postEndpoint"]

    s3_response = upload_to_s3(signature, end_point, file_path)
    if not str(s3_response.status_code).startswith("2"):
        # TODO fix the import
        process_response(s3_response)

    if s3_response.status_code == 400:
        print(f"Detail: Bad request when uploading to AWS S3 -- file: {file_path}")

    return {"key": key, "id": image_id}


def sign_upload(client, image_id, key, file_path):
    file_format = Path(file_path).suffix
    return client.post(
        f"/dataset_images/{image_id}/sign_upload?key={key}",
        payload={"filePath": file_path, "contentType": f"image/{file_format}"},
    )


def upload_to_s3(signature, end_point, file_path=None):
    test = {}
    test["file"] = open(file_path, "rb")
    response = requests.post("http:" + end_point, data=signature, files=test)
    return response
