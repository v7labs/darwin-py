from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import List, Optional

import darwin
from darwin.dataset.download_manager import \
    download_all_images_from_annotations
from darwin.dataset.upload_manager import (_split_on_file_type,
                                           upload_file_to_s3)
from darwin.utils import urljoin


class RemoteDataset:
    def __init__(self, name: str, *, slug: Optional[str] = None, dataset_id: int,
                 project_id: int, image_count: int = 0, progress: int = 0,
                 client: darwin.client.Client):
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
        images, videos = _split_on_file_type(filenames)
        data = self._client.put(endpoint=f"/datasets/{self.dataset_id}",
                                payload={"image_filenames": images,
                                         "videos": [{"fps": fps, "original_filename": video} for video in videos]})

        for image_file in data["image_data"]:
            metadata = upload_file_to_s3(self._client, image_file)
            self._client.put(f"/dataset_images/{metadata['id']}/confirm_upload",
                             payload={})
            yield

        for video_file in data["video_data"]:
            metadata = upload_file_to_s3(self._client, video_file)
            self._client.put(f"/dataset_videos/{metadata['id']}/confirm_upload",
                             payload={})
            yield

    def pull(self):
        """Downloads a rermote project (images and annotations) in the projects directory. """
        response = self._client.get(
            f"/datasets/{self.dataset_id}/export?format=json", raw=True
        )
        zip_file = io.BytesIO(response.content)
        if zipfile.is_zipfile(zip_file):
            z = zipfile.ZipFile(zip_file)
            project_dir = Path(self._client.project_dir) / self.slug
            images_dir = project_dir / "images"
            annotations_dir = project_dir / "annotations"
            annotations_dir.mkdir(parents=True, exist_ok=True)

            z.extractall(annotations_dir)
            annotation_format = "json"
            return download_all_images_from_annotations(self._client.url,
                                                        annotations_dir,
                                                        images_dir,
                                                        annotation_format)

    def local(self):
        return darwin.dataset.LocalDataset(project_path=Path(self._client.project_dir) / self.slug,
                                           client=self._client)

    @property
    def url(self):
        return urljoin(self._client.base_url, f"/datasets/{self.project_id}")

    def remove(self):
        self._client.put(f"projects/{self.project_id}/archive", payload={})
