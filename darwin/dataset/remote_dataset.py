import io
import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from darwin.dataset.download_manager import download_all_images_from_annotations
from darwin.dataset.upload_manager import add_files_to_dataset
from darwin.dataset.utils import exhaust_generator
from darwin.dataset.release import Release
from darwin.exceptions import NotFound
from darwin.utils import find_files, urljoin

if TYPE_CHECKING:
    from darwin.client import Client


class RemoteDataset:
    def __init__(
        self,
        *,
        team: str,
        name: str,
        slug: Optional[str] = None,
        dataset_id: int,
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
        image_count : int
            Dataset size (number of images)
        progress : float
            How much of the dataset has been annotated 0.0 to 1.0 (1.0 == 100%)
        client : Client
            Client to use for interaction with the server
        """
        self.team = team
        self.name = name
        self.slug = slug or name
        self.dataset_id = dataset_id
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
        resume : bool
            Flag for signalling the resuming of a push

        Returns
        -------
        generator : function
            Generator for doing the actual uploads. This is None if blocking is True
        count : int
            The files count
        """

        # This is where the responses from the upload function will be saved/load for resume
        self.local_path.parent.mkdir(exist_ok=True)
        responses_path = self.local_path.parent / ".upload_responses.json"
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
            files_to_exclude.extend(
                [
                    response["file_path"]
                    for response in logged_responses
                    if response["s3_response_status_code"].startswith("2")
                ]
            )

        files_to_upload = find_files(
            files=files_to_upload, recursive=True, files_to_exclude=files_to_exclude
        )

        if not files_to_upload:
            raise ValueError(
                "No files to upload, check your path, exclusion filters and resume flag"
            )

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
                responses = [{k: str(v) for k, v in response.items()} for response in responses]
                if resume:
                    responses.extend(logged_responses)
                with responses_path.open("w") as f:
                    json.dump(responses, f)
            return None, count
        else:
            return progress, count

    def pull(
        self, release: Release, blocking: bool = True, multi_threaded: bool = True, only_done_images: bool = True
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
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_file_path = release.download_zip(Path(tmp_dir) / "dataset.zip")
            with zipfile.ZipFile(zip_file_path) as z:
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
                for annotation_path in annotations_dir.glob(f"*.json"):
                    annotation_path.rename(annotation_path.parent / f"V7_{annotation_path.name}")
                progress, count = download_all_images_from_annotations(
                    self.client.url, annotations_dir, images_dir, "json"
                )
                # If blocking is selected, download the dataset on the file system
                if blocking:
                    exhaust_generator(progress=progress(), count=count, multi_threaded=multi_threaded)
                    return None, count
                else:
                    return progress, count

    def remove_remote(self):
        """Archives (soft-deletion) the remote dataset"""
        self.client.put(f"datasets/{self.dataset_id}/archive", payload={})

    def get_report(self, granularity="day"):
        return self.client.get(
            f"/reports/{self.dataset_id}/annotation?group_by=dataset,user&dataset_ids={self.dataset_id}&granularity={granularity}&format=csv&include=dataset.name,user.first_name,user.last_name,user.email",
            raw=True,
        ).text

    def get_releases(self):
        releases_json = self.client.get(f"/datasets/{self.dataset_id}/exports")
        releases = [Release.parse_json(self.slug, self.team, payload) for payload in releases_json]
        return sorted(releases, key=lambda x: x.version, reverse=True)

    def get_release(self, version):
        releases = self.get_releases()
        if not releases:
            raise NotFound()

        if version == "latest":
            return releases[0]
        
        for release in releases:
            if str(release.version) == version:
                return release
        raise NotFound()

    @property
    def remote_path(self) -> Path:
        """Returns an URL specifying the location of the remote dataset"""
        return urljoin(self.client.base_url, f"/datasets/{self.dataset_id}")

    @property
    def local_path(self) -> Path:
        """Returns a Path to the local dataset"""
        if self.slug is not None:
            return Path(self.client.datasets_dir) / self.slug
        else:
            return Path(self.client.datasets_dir)
