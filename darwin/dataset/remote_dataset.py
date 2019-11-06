import io
import json
import shutil
import zipfile
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

from darwin.dataset.download_manager import download_all_images_from_annotations
from darwin.dataset.upload_manager import add_files_to_dataset
from darwin.dataset.utils import exhaust_generator
from darwin.exceptions import NotFound
from darwin.utils import find_files, urljoin

if TYPE_CHECKING:
    from darwin.client import Client


class RemoteDataset:
    def __init__(
        self,
        *,
        name: str,
        slug: Optional[str] = None,
        dataset_id: int,
        project_id: int,
        image_count: int = 0,
        progress: float = 0,
        client: "Client",
    ):
        """Inits a DarwinDataset.
        This class manages the remote and local versions of a dataset hosted on Darwin.
        It allows several dataset management operations such as syncing between
        remote and local, pulling a remote dataset, removing the local files, ...

        Parameters
        ----------
        name : str
            Name of the datasets as originally displayed on Darwin.
            It may contain white spaces, capital letters and special characters, e.g. `Bird Species!`
        slug : str
            This is the dataset name with everything lower-case, removed specials characters and
            spaces are replaced by dashes, e.g., `bird-species`. This string is unique within a team
        dataset_id : int
            Unique internal reference from the Darwin backend
        project_id : int
            [Deprecated] will be removed in next iteration
        image_count : int
            Dataset size (number of images)
        progress : float
            How much of the dataset has been annotated 0.0 to 1.0 (1.0 == 100%)
        client : Client
            Client to use for interaction with the server
        """
        self.name = name
        self.slug = slug or name
        self.dataset_id = dataset_id
        self.project_id = project_id
        self.image_count = image_count
        self.progress = progress
        self.client = client

    def push(
        self,
        blocking: bool = True,
        multi_threaded: bool = True,
        fps: int = 1,
        files_to_exclude: Optional[List[str]] = None,
        files_to_upload: Optional[List[str]] = None,
        source_folder: Optional[Path] = None,
        resume: bool = False,
    ):
        """Uploads a local project (images ONLY) in the projects directory.

        Parameters
        ----------
        blocking : bool
            If False, the dataset is not uploaded and a generator function is returned instead
        multi_threaded : bool
            Uses multiprocessing to upload the dataset in parallel.
            If blocking is False this has no effect.
        files_to_exclude : list[str]
            List of files to exclude from the file scan (which is done only if files is None)
        files_to_upload : list[Path]
            List of files to upload
        fps : int
            Number of file per seconds to upload
        source_folder: Path
            Path to the source folder where to scan for files.
            If not specified self.local_path / "images" is used instead
        resume : bool
            Flag for signalling the resuming of a push

        Returns
        -------
        generator : function
            Generator for doing the actual uploads. This is None if blocking is True
        count : int
            The files count
        """
        # Resolving where to look for images
        if source_folder is None:
            source_folder = self.local_path / "images"
        # This is where the responses from the upload function will be saved/load for resume
        responses_path = source_folder.parent / "upload_responses.json"
        # Init optional parameters
        if files_to_exclude is None:
            files_to_exclude = []
        if files_to_upload is None and not source_folder.exists():
            raise NotFound("Dataset location not found. Check your path.")

        if resume:
            if not responses_path.exists():
                raise NotFound("Dataset location not found. Check your path.")
            with responses_path.open() as f:
                logged_responses = json.load(f)
            files_to_exclude.extend([response['file_path']
                                     for response in logged_responses
                                     if response['s3_response_status_code'].startswith("2")])

        files_to_upload = find_files(
            root = source_folder,
            files_list = files_to_upload,
            recursive = True,
            files_to_exclude= files_to_exclude
        )

        if not files_to_upload:
            raise NotFound("No files to upload, check your path, exclusion filters and resume flag")

        progress, count = add_files_to_dataset(
            client=self.client, dataset_id=str(self.dataset_id), filenames=files_to_upload, fps=fps
        )

        # If blocking is selected, upload the dataset remotely
        if blocking:
            responses = exhaust_generator(
                progress=progress, count=count, multi_threaded=multi_threaded
            )
            # Log responses to file
            if responses:
                responses = [{k: str(v) for k, v in response.items()} for response in responses ]
                if resume:
                    responses.extend(logged_responses)
                with responses_path.open('w') as f:
                    json.dump(responses, f)
            return None, count
        else:
            return progress, count


    def pull(
        self,
        blocking: bool = True,
        multi_threaded: bool = True,
        only_done_images: bool = True,
    ):
        """Downloads a remote project (images and annotations) in the projects directory.

        Parameters
        ----------
        blocking : bool
            If False, the dataset is not downloaded and a generator function is returned instead
        multi_threaded : bool
            Uses multiprocessing to download the dataset in parallel. If blocking is False this has no effect.
        only_done_images: bool
            If False, it will also download images without annotations or that have not been marked as Done

        Returns
        -------
        generator : function
            Generator for doing the actual downloads. This is None if blocking is True
        count : int
            The files count
        """
        annotation_format = "json"
        query = f"/datasets/{self.dataset_id}/export?format={annotation_format}"
        if only_done_images:
            query += f"&image_status=done"
        response = self.client.get(query, raw=True)
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
                self.client.url, annotations_dir, images_dir, annotation_format
            )
            # If blocking is selected, download the dataset on the file system
            if blocking:
                exhaust_generator(progress=progress(), count=count, multi_threaded=multi_threaded)
                return None, count
            else:
                return progress, count

    def remove_remote(self):
        """Archives (soft-deletion) the remote dataset"""
        self.client.put(f"projects/{self.project_id}/archive", payload={})

    @property
    def remote_path(self) -> Path:
        """Returns an URL specifying the location of the remote dataset"""
        return Path(urljoin(self.client.base_url, f"/datasets/{self.project_id}"))

    @property
    def local_path(self) -> Path:
        """Returns a Path to the local dataset"""
        if self.slug is not None:
            return Path(self.client.projects_dir) / self.slug
        else:
            return Path(self.client.projects_dir)
