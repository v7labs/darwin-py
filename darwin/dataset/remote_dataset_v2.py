from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Tuple, Union

from darwin.dataset import RemoteDataset
from darwin.dataset.release import Release
from darwin.dataset.upload_manager import (
    FileUploadCallback,
    LocalFile,
    ProgressCallback,
    UploadHandler,
    UploadHandlerV2,
)
from darwin.dataset.utils import is_relative_to
from darwin.datatypes import ItemId, PathLike
from darwin.exceptions import NotFound, UnknownExportVersion
from darwin.item import DatasetItem
from darwin.item_sorter import ItemSorter
from darwin.utils import find_files, urljoin
from requests.models import Response

if TYPE_CHECKING:
    from darwin.client import Client


class RemoteDatasetV2(RemoteDataset):
    """
    Manages the remote and local versions of a dataset hosted on Darwin.
    It allows several dataset management operations such as syncing between
    remote and local, pulling a remote dataset, removing the local files, ...

    Parameters
    ----------
    client : Client
        Client to use for interaction with the server.
    team : str
        Team the dataset belongs to.
    name : str
        Name of the datasets as originally displayed on Darwin.
        It may contain white spaces, capital letters and special characters, e.g. `Bird Species!`.
    slug : str
        This is the dataset name with everything lower-case, removed specials characters and
        spaces are replaced by dashes, e.g., `bird-species`. This string is unique within a team.
    dataset_id : int
        Unique internal reference from the Darwin backend.
    item_count : int, default: 0
        Dataset size (number of items).
    progress : float, default: 0
        How much of the dataset has been annotated 0.0 to 1.0 (1.0 == 100%).

    Attributes
    ----------
    client : Client
        Client to use for interaction with the server.
    team : str
        Team the dataset belongs to.
    name : str
        Name of the datasets as originally displayed on Darwin.
        It may contain white spaces, capital letters and special characters, e.g. `Bird Species!`.
    slug : str
        This is the dataset name with everything lower-case, removed specials characters and
        spaces are replaced by dashes, e.g., `bird-species`. This string is unique within a team.
    dataset_id : int
        Unique internal reference from the Darwin backend.
    item_count : int, default: 0
        Dataset size (number of items).
    progress : float, default: 0
        How much of the dataset has been annotated 0.0 to 1.0 (1.0 == 100%).
    """

    def __init__(
        self,
        *,
        client: "Client",
        team: str,
        name: str,
        slug: str,
        dataset_id: int,
        item_count: int = 0,
        progress: float = 0,
    ):
        super().__init__(
            client=client,
            team=team,
            name=name,
            slug=slug,
            dataset_id=dataset_id,
            item_count=item_count,
            progress=progress,
            version=2,
        )

    def get_releases(self) -> List["Release"]:
        """
        Get a sorted list of releases with the most recent first.

        Returns
        -------
        List["Release"]
            Returns a sorted list of available ``Release``\\s with the most recent first.
        """
        try:
            releases_json: List[Dict[str, Any]] = self.client.api_v2.get_exports(self.slug, team_slug=self.team)
        except NotFound:
            return []

        releases = [Release.parse_json(self.slug, self.team, payload) for payload in releases_json]
        return sorted(filter(lambda x: x.available, releases), key=lambda x: x.version, reverse=True)

    def push(
        self,
        files_to_upload: Optional[List[Union[PathLike, LocalFile]]],
        *,
        blocking: bool = True,
        multi_threaded: bool = True,
        max_workers: Optional[int] = None,
        fps: int = 0,
        as_frames: bool = False,
        extract_views: bool = False,
        files_to_exclude: Optional[List[PathLike]] = None,
        path: Optional[str] = None,
        preserve_folders: bool = False,
        progress_callback: Optional[ProgressCallback] = None,
        file_upload_callback: Optional[FileUploadCallback] = None,
    ) -> UploadHandler:
        """
        Uploads a local dataset (images ONLY) in the datasets directory.

        Parameters
        ----------
        files_to_upload : Optional[List[Union[PathLike, LocalFile]]]
            List of files to upload. Those can be folders.
        blocking : bool, default: True
            If False, the dataset is not uploaded and a generator function is returned instead.
        multi_threaded : bool, default: True
            Uses multiprocessing to upload the dataset in parallel.
            If blocking is False this has no effect.
        max_workers : int, default: None
            Maximum number of workers to use for parallel upload.
        fps : int, default: 0
            When the uploading file is a video, specify its framerate.
        as_frames: bool, default: False
            When the uploading file is a video, specify whether it's going to be uploaded as a list of frames.
        extract_views: bool, default: False
            When the uploading file is a volume, specify whether it's going to be split into orthogonal views.
        files_to_exclude : Optional[PathLike]], default: None
            Optional list of files to exclude from the file scan. Those can be folders.
        path: Optional[str], default: None
            Optional path to store the files in.
        preserve_folders : bool, default: False
            Specify whether or not to preserve folder paths when uploading
        progress_callback: Optional[ProgressCallback], default: None
            Optional callback, called every time the progress of an uploading files is reported.
        file_upload_callback: Optional[FileUploadCallback], default: None
            Optional callback, called every time a file chunk is uploaded.

        Returns
        -------
        handler : UploadHandler
           Class for handling uploads, progress and error messages.

        Raises
        ------
        ValueError
            - If ``files_to_upload`` is ``None``.
            - If a path is specified when uploading a LocalFile object.
            - If there are no files to upload (because path is wrong or the exclude filter excludes everything).
        """
        if files_to_exclude is None:
            files_to_exclude = []

        if files_to_upload is None:
            raise ValueError("No files or directory specified.")

        uploading_files = [item for item in files_to_upload if isinstance(item, LocalFile)]
        search_files = [item for item in files_to_upload if not isinstance(item, LocalFile)]

        generic_parameters_specified = path is not None or fps != 0 or as_frames is not False
        if uploading_files and generic_parameters_specified:
            raise ValueError("Cannot specify a path when uploading a LocalFile object.")

        for found_file in find_files(search_files, files_to_exclude=files_to_exclude):
            local_path = path
            if preserve_folders:
                source_files = [source_file for source_file in search_files if is_relative_to(found_file, source_file)]
                if source_files:
                    local_path = str(found_file.relative_to(source_files[0]).parent)
            uploading_files.append(
                LocalFile(found_file, fps=fps, as_frames=as_frames, extract_views=extract_views, path=local_path)
            )

        if not uploading_files:
            raise ValueError("No files to upload, check your path, exclusion filters and resume flag")

        handler = UploadHandlerV2(self, uploading_files)
        if blocking:
            handler.upload(
                max_workers=max_workers,
                multi_threaded=multi_threaded,
                progress_callback=progress_callback,
                file_upload_callback=file_upload_callback,
            )
        else:
            handler.prepare_upload()

        return handler

    def fetch_remote_files(
        self, filters: Optional[Dict[str, Union[str, List[str]]]] = None, sort: Optional[Union[str, ItemSorter]] = None
    ) -> Iterator[DatasetItem]:
        """
        Fetch and lists all files on the remote dataset.

        Parameters
        ----------
        filters : Optional[Dict[str, Union[str, List[str]]]], default: None
            The filters to use. Files excluded by the filter won't be fetched.
        sort : Optional[Union[str, ItemSorter]], default: None
            A sorting direction. It can be a string with the values 'asc', 'ascending', 'desc',
            'descending' or an ``ItemSorter`` instance.

        Yields
        -------
        Iterator[DatasetItem]
            An iterator of ``DatasetItem``.
        """
        post_filters: List[Tuple[str, Any]] = []
        post_sort: Dict[str, str] = {}

        if filters:
            if "filenames" in filters:
                # compability layer with v1
                filters["item_names"] = filters["filenames"]
                del filters["filenames"]

            for list_type in ["item_names", "statuses", "item_ids", "slot_types"]:
                if list_type in filters:
                    if type(filters[list_type]) is list:
                        for value in filters[list_type]:
                            post_filters.append(("{}[]".format(list_type), value))
                    else:
                        post_filters.append((list_type, str(filters[list_type])))

        if sort:
            item_sorter = ItemSorter.parse(sort)
            post_sort[f"sort[{item_sorter.field}]"] = item_sorter.direction.value
        cursor = {"page[size]": 500}
        while True:
            query = post_filters + list(post_sort.items()) + list(cursor.items())
            response = self.client.api_v2.fetch_items(self.dataset_id, query, team_slug=self.team)
            yield from [DatasetItem.parse(item) for item in response["items"]]

            if response["page"]["next"]:
                cursor["page[from]"] = response["page"]["next"]
            else:
                return

    def archive(self, items: Iterator[DatasetItem]) -> None:
        """
        Archives (soft-deletion) the given ``DatasetItem``\\s belonging to this ``RemoteDataset``.

        Parameters
        ----------
        items : Iterator[DatasetItem]
            The ``DatasetItem``\\s to be archived.
        """
        payload: Dict[str, Any] = {
            "filters": {"item_ids": [item.id for item in items], "dataset_ids": [self.dataset_id]}
        }
        self.client.api_v2.archive_items(payload, team_slug=self.team)

    def restore_archived(self, items: Iterator[DatasetItem]) -> None:
        """
        Restores the archived ``DatasetItem``\\s that belong to this ``RemoteDataset``.

        Parameters
        ----------
        items : Iterator[DatasetItem]
            The ``DatasetItem``\\s to be restored.
        """
        payload: Dict[str, Any] = {
            "filters": {"item_ids": [item.id for item in items], "dataset_ids": [self.dataset_id]}
        }
        self.client.api_v2.restore_archived_items(payload, team_slug=self.team)

    def move_to_new(self, items: Iterator[DatasetItem]) -> None:
        """
        Changes the given ``DatasetItem``\\s status to ``new``.

        Parameters
        ----------
        items : Iterator[DatasetItem]
            The ``DatasetItem``\\s whose status will change.
        """

        (workflow_id, stages) = self._fetch_stages("dataset")
        if not stages:
            raise ValueError("Dataset's workflow is missing a dataset stage")

        self.client.api_v2.move_to_stage(
            {"item_ids": [item.id for item in items], "dataset_ids": [self.dataset_id]},
            stages[0]["id"],
            workflow_id,
            team_slug=self.team,
        )

    def reset(self, items: Iterator[DatasetItem]) -> None:
        """
        Deprecated
        Resets the  given ``DatasetItem``\\s.

        Parameters
        ----------
        items : Iterator[DatasetItem]
            The ``DatasetItem``\\s to be resetted.
        """
        raise ValueError("Reset is deprecated for version 2 datasets")

    def complete(self, items: Iterator[DatasetItem]) -> None:
        """
        Completes the given ``DatasetItem``\\s.

        Parameters
        ----------
        items : Iterator[DatasetItem]
            The ``DatasetItem``\\s to be completed.
        """
        (workflow_id, stages) = self._fetch_stages("complete")
        if not stages:
            raise ValueError("Dataset's workflow is missing a complete stage")

        self.client.api_v2.move_to_stage(
            {"item_ids": [item.id for item in items], "dataset_ids": [self.dataset_id]},
            stages[0]["id"],
            workflow_id,
            team_slug=self.team,
        )

    def delete_items(self, items: Iterator[DatasetItem]) -> None:
        """
        Deletes the given ``DatasetItem``\\s.

        Parameters
        ----------
        items : Iterator[DatasetItem]
            The ``DatasetItem``\\s to be deleted.
        """
        self.client.api_v2.delete_items(
            {"dataset_ids": [self.dataset_id], "item_ids": [item.id for item in items]}, team_slug=self.team
        )

    def export(
        self,
        name: str,
        annotation_class_ids: Optional[List[str]] = None,
        include_url_token: bool = False,
        include_authorship: bool = False,
        version: Optional[str] = None,
    ) -> None:
        """
        Create a new release for this ``RemoteDataset``.

        Parameters
        ----------
        name : str
            Name of the release.
        annotation_class_ids : Optional[List[str]], default: None
            List of the classes to filter.
        include_url_token : bool, default: False
            Should the image url in the export include a token enabling access without team
            membership or not?
        include_authorship : bool, default: False
            If set, include annotator and reviewer metadata for each annotation.
        version : Optional[str], default: None, enum: ["1.0", "2.0"]
            When used for V2 dataset, allows to force generation of either Darwin JSON 1.0 (Legacy) or newer 2.0.
            Omit this option to get your team's default.
        """
        str_version = str(version)
        if str_version == "2.0":
            format = "darwin_json_2"
        elif str_version == "1.0":
            format = "json"
        elif version == None:
            format = None
        else:
            raise UnknownExportVersion(version)

        self.client.api_v2.export_dataset(
            format=format,
            name=name,
            include_authorship=include_authorship,
            include_token=include_url_token,
            annotation_class_ids=annotation_class_ids,
            filters=None,
            dataset_slug=self.slug,
            team_slug=self.team,
        )

    def get_report(self, granularity: str = "day") -> str:
        """
        Returns a String representation of a CSV report for this ``RemoteDataset``.

        Parameters
        ----------
        granularity : str, default: "day"
            The granularity of the report, can be 'day', 'week' or 'month'.

        Returns
        -------
        str
            A CSV report.
        """
        response: Response = self.client.get_report(self.dataset_id, granularity, self.team)
        return response.text

    def workview_url_for_item(self, item: DatasetItem) -> str:
        """
        Returns the darwin URL for the given ``DatasetItem``.

        Parameters
        ----------
        item : DatasetItem
            The ``DatasetItem`` for which we want the url.

        Returns
        -------
        str
            The url.
        """
        return urljoin(self.client.base_url, f"/workview?dataset={self.dataset_id}&item={item.id}")

    def post_comment(
        self, item: DatasetItem, text: str, x: float, y: float, w: float, h: float, slot_name: Optional[str] = None
    ):
        """
        Adds a comment to an item in this dataset,
        Tries to infer slot_name if left out.
        """
        if not slot_name:
            if len(item.slots) != 1:
                raise ValueError(f"Unable to infer slot for '{item.id}', has multiple slots: {','.join(item.slots)}")
            slot_name = item.slots[0]["slot_name"]

        self.client.api_v2.post_comment(item.id, text, x, y, w, h, slot_name, team_slug=self.team)

    def import_annotation(self, item_id: ItemId, payload: Dict[str, Any]) -> None:
        """
        Imports the annotation for the item with the given id.

        Parameters
        ----------
        item_id: ItemId
            Identifier of the Item that we are import the annotation to.
        payload: Dict[str, Any]
            A dictionary with the annotation to import. The default format is:
            `{"annotations": serialized_annotations, "overwrite": "false"}`
        """

        self.client.api_v2.import_annotation(item_id, payload=payload, team_slug=self.team)

    def _fetch_stages(self, stage_type):
        detailed_dataset = self.client.api_v2.get_dataset(self.dataset_id)
        workflow_ids = detailed_dataset["workflow_ids"]
        if len(workflow_ids) == 0:
            raise ValueError("Dataset is not part of a workflow")
        # currently we can only be part of one workflow
        workflow_id = workflow_ids[0]
        workflow = self.client.api_v2.get_workflow(workflow_id, team_slug=self.team)
        return (workflow_id, [stage for stage in workflow["stages"] if stage["type"] == stage_type])
