import datetime
import io
import json
import shutil
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import requests

from darwin.exceptions import UnsupportedFileType
from darwin.utils import urljoin

if TYPE_CHECKING:
    from darwin.client import Client

SUPPORTED_IMAGE_EXTENSIONS = [".png", ".jpeg", ".jpg"]
SUPPORTED_VIDEO_EXTENSIONS = [".bpm", ".mov", ".mp4"]


class LocalDataset:
    def __init__(self, project_path: Path, client: "Client"):
        self.project_path = project_path
        self.name = project_path.name
        self.slug = project_path.name
        self._client = client

    @property
    def image_count(self) -> int:
        return sum(
            1
            for p in (self.project_path / "images").glob("*")
            if p.suffix in SUPPORTED_IMAGE_EXTENSIONS
        )

    @property
    def disk_size(self) -> int:
        return sum(path.stat().st_size for path in self.project_path.glob("**"))

    @property
    def sync_date(self) -> datetime.datetime:
        timestamp = self.project_path.stat().st_mtime
        return datetime.datetime.fromtimestamp(timestamp)

    def remove(self):
        shutil.rmtree(self.project_path)


class Dataset:
    def __init__(
        self,
        name: str,
        *,
        slug: Optional[str] = None,
        dataset_id: int,
        project_id: int,
        image_count: int = 0,
        progress: int = 0,
        client: "Client",
    ):
        self.name = name
        self.slug = slug or name
        self.dataset_id = dataset_id
        self.project_id = project_id
        self.image_count = image_count
        self.progress = progress
        self._client = client

    def upload_files(self, files: List[str], fps: int = 1):
        """ A generator where each file is emitted upon upload """
        yield from self._add_files_to_dataset(files, fps=fps)

    def _add_files_to_dataset(self, filenames: List, fps: int):
        """Helper function: upload images to an existing remote dataset. """
        if not filenames:
            return

        for filenames_chunk in chunk(filenames, 100):
            images, videos = split_on_file_type(filenames_chunk)
            data = self._client.put(
                f"/datasets/{self.dataset_id}",
                {
                    "image_filenames": [Path(image).name for image in images],
                    "videos": [
                        {"fps": fps, "original_filename": Path(video).name} for video in videos
                    ],
                },
            )
            for image_file in data["image_data"]:
                metadata = upload_file_to_s3(self._client, image_file, images)
                self._client.put(f"/dataset_images/{metadata['id']}/confirm_upload", payload={})
                yield

            for video_file in data["video_data"]:
                metadata = upload_file_to_s3(self._client, video_file, videos)
                self._client.put(f"/dataset_videos/{metadata['id']}/confirm_upload", payload={})
                yield

    def pull(self, image_status: Optional[str] = None):
        """Downloads a remote project (images and annotations) in the projects directory. """
        query = f"/datasets/{self.dataset_id}/export?format=json"
        if image_status is not None:
            query += f"&image_status={image_status}"

        response = self._client.get(query, raw=True)
        zip_file = io.BytesIO(response.content)
        if zipfile.is_zipfile(zip_file):
            z = zipfile.ZipFile(zip_file)
            project_dir = Path(self._client.project_dir) / self.slug
            images_dir = project_dir / "images"
            annotations_dir = project_dir / "annotations"
            annotations_dir.mkdir(parents=True, exist_ok=True)

            z.extractall(annotations_dir)
            annotation_format = "json"
            return download_all_images_from_annotations(
                self._client._url, annotations_dir, images_dir, annotation_format
            )

    def local(self):
        return LocalDataset(
            project_path=Path(self._client.project_dir) / self.slug, client=self._client
        )

    @property
    def url(self):
        return urljoin(self._client._base_url, f"/datasets/{self.project_id}")

    def remove(self):
        self._client.put(f"projects/{self.project_id}/archive", payload={})


def split_on_file_type(files: List[str]):
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


def upload_file_to_s3(
    client: "Client", file: Dict[str, Any], full_path: List[str]
) -> Dict[str, Any]:
    """Helper function: upload data to AWS S3"""
    key = file["key"]
    file_path = [path for path in full_path if Path(path).name == file["original_filename"]][0]
    image_id = file["id"]

    response = sign_upload(client, image_id, key, Path(file_path).suffix)
    signature = response["signature"]
    end_point = response["postEndpoint"]

    s3_response = upload_to_s3(signature, end_point, file_path)
    # if not str(s3_response.status_code).startswith("2"):
    #     process_response(s3_response)

    if s3_response.status_code == 400:
        print(f"Detail: Bad request when uploading to AWS S3 -- file: {file_path}")

    return {"key": key, "id": image_id}


def sign_upload(client, image_id, key, file_suffix):
    return client.post(
        f"/dataset_images/{image_id}/sign_upload?key={key}",
        payload={"contentType": f"image/{file_suffix}"},
    )


def upload_to_s3(signature, end_point, file_path=None):
    test = {}
    test["file"] = open(file_path, "rb")
    response = requests.post("http:" + end_point, data=signature, files=test)
    return response


def download_all_images_from_annotations(
    api_url: str, annotations_path: Path, images_path: Path, annotation_format="json"
):
    """Helper function: downloads an image given a .json annotation path. """
    images_path.mkdir(exist_ok=True)

    if annotation_format not in ["json", "xml"]:
        print(f"Annotation format {annotation_format} not supported")
        return

    # return both the count and a generator for doing the actual downloads
    count = sum(1 for _ in annotations_path.glob(f"*.{annotation_format}"))
    generator = lambda: (
        download_image_from_annotation(api_url, annotation_path, images_path, annotation_format)
        for annotation_path in annotations_path.glob(f"*.{annotation_format}")
    )
    return generator, count


def download_image_from_annotation(
    api_url: str, annotation_path: Path, images_path: Path, annotation_format: str
):
    """Helper function: downloads the all images corresponsing to a project. """
    if annotation_format == "json":
        download_image_from_json_annotation(api_url, annotation_path, images_path)
    elif annotation_format == "xml":
        print("sorry can't let you do that dave")
        # TODO: fix me
        # download_image_from_xml_annotation(annotation_path, images_path)


def download_image_from_json_annotation(api_url: str, annotation_path: Path, images_path: Path):
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
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(path, "wb") as file:
            for chunk in response:
                file.write(chunk)
    else:
        print(response.status_code, response.json())
        raise FailedToDownloadImage()


class FailedToDownloadImage(Exception):
    pass


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
