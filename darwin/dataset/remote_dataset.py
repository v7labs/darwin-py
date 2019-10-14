from __future__ import annotations

import io
import multiprocessing as mp
import shutil
import zipfile
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

from tqdm import tqdm

import darwin
from darwin.dataset.download_manager import download_all_images_from_annotations
from darwin.dataset.upload_manager import _split_on_file_type, upload_file_to_s3
from darwin.utils import urljoin

if TYPE_CHECKING:
    from darwin.client import Client


class RemoteDataset:
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
        for filenames_chunk in RemoteDataset.chunk(filenames, 100):
            images, videos = _split_on_file_type(filenames_chunk)
            data = self._client.put(
                endpoint=f"/datasets/{self.dataset_id}",
                payload={"image_filenames": images,
                         "videos": [{"fps": fps, "original_filename": video} for video in videos]}
            )

        for image_file in data["image_data"]:
            metadata = upload_file_to_s3(self._client, image_file)
            self._client.put(f"/dataset_images/{metadata['id']}/confirm_upload", payload={})
            yield

        for video_file in data["video_data"]:
            metadata = upload_file_to_s3(self._client, video_file)
            self._client.put(f"/dataset_videos/{metadata['id']}/confirm_upload", payload={})
            yield

    @staticmethod
    def _f(x):
        """Support function for pool.map() in pull()"""
        x()

    def pull(self, blocking: Optional[bool] = True, multi_threaded: Optional[bool] = True):
        """Downloads a remote project (images and annotations) in the projects directory.

        Parameters
        ----------
        blocking : bool
            If False, the dataset is not donwloaded and a generator function is returned instead
        multi_threaded : bool
            Uses multiprocessing to download the dataset in parallel. If blocking is False this has no effect.

        Returns
        -------
        generator : function
            Generator for doing the actual downloads. This is None if blocking is True
        count : int
            The files count
        """
        annotation_format = "json"
        response = self._client.get(f"/datasets/{self.dataset_id}/export?format=json", raw=True)
        zip_file = io.BytesIO(response.content)
        if zipfile.is_zipfile(zip_file):
            z = zipfile.ZipFile(zip_file)
            images_dir = self.local_path / "images"
            annotations_dir = self.local_path / "annotations"
            if annotations_dir.exists():
                try:
                    shutil.rmtree(annotations_dir)
                except PermissionError:
                    print(f"Could not remove dataset in {annotations_dir}. Permission denied.")
            annotations_dir.mkdir(parents=True, exist_ok=False)
            z.extractall(annotations_dir)
            # Rename all json files pre-pending 'V7_' in front of them.
            # This is necessary to avoid overriding them in a later stage.
            for annotation_path in annotations_dir.glob(f"*.{annotation_format}"):
                annotation_path.rename(annotation_path.parent / f"V7_{annotation_path.name}")
            progress, count = download_all_images_from_annotations(
                self._client.url, annotations_dir, images_dir, annotation_format
            )
            # If blocking is selected, download the dataset on the file system
            if blocking:
                if multi_threaded:
                    pbar = tqdm(total=count)
                    def update(*a):
                        pbar.update()
                    with mp.Pool(mp.cpu_count()) as pool:
                        for f in progress():
                            pool.apply_async(RemoteDataset._f, args=(f,), callback=update)
                        pool.close()
                        pool.join()
                else:
                    for f in tqdm(progress(), total=count, desc="Downloading"):
                        f()
                return None, count
            else:
                return progress, count

    def local(self):
        return darwin.dataset.LocalDataset(
            project_path=self.local_path, client=self._client
        )

    @property
    def url(self):
        return urljoin(self._client.base_url, f"/datasets/{self.project_id}")

    def remove(self):
        self._client.put(f"projects/{self.project_id}/archive", payload={})

    @property
    def local_path(self):
        return Path(self._client.project_dir) / self.slug

    @staticmethod
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
            yield from RemoteDataset.chunk(left_over, size)
        if current_list:
            yield current_list
