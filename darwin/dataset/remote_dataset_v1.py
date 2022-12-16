import itertools
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Union
from xml.dom import ValidationErr

from darwin.dataset.release import Release
from darwin.dataset.upload_manager import (
    FileUploadCallback,
    LocalFile,
    ProgressCallback,
    UploadHandler,
    UploadHandlerV1,
)
from darwin.dataset.utils import is_relative_to
from darwin.datatypes import ItemId, PathLike
from darwin.exceptions import NotFound, ValidationError
from darwin.item import DatasetItem
from darwin.item_sorter import ItemSorter
from darwin.utils import find_files, urljoin
from requests.models import Response

if TYPE_CHECKING:
    from darwin.client import Client

from darwin.dataset import RemoteDataset


class RemoteDatasetV1(RemoteDataset):
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
            releases_json: List[Dict[str, Any]] = self.client.get_exports(self.dataset_id, self.team)
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
            uploading_files.append(LocalFile(found_file, fps=fps, as_frames=as_frames, path=local_path))

        if not uploading_files:
            raise ValueError("No files to upload, check your path, exclusion filters and resume flag")

        handler = UploadHandlerV1(self, uploading_files)
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
        post_filters: Dict[str, Union[str, List[str]]] = {}
        post_sort: Dict[str, str] = {}

        if filters:
            for list_type in ["filenames", "statuses"]:
                if list_type in filters:
                    if type(filters[list_type]) is list:
                        post_filters[list_type] = filters[list_type]
                    else:
                        post_filters[list_type] = str(filters[list_type])
            if "path" in filters:
                post_filters["path"] = str(filters["path"])
            if "item_ids" in filters:
                post_filters["dataset_item_ids"] = filters["item_ids"]
            if "types" in filters:
                post_filters["types"] = str(filters["types"])

            if sort:
                item_sorter = ItemSorter.parse(sort)
                post_sort[item_sorter.field] = item_sorter.direction.value
        cursor = {"page[size]": 500}
        while True:
            payload = {"filter": post_filters, "sort": post_sort}
            response = self.client.fetch_remote_files(self.dataset_id, cursor, payload, self.team)

            yield from [DatasetItem.parse(item) for item in response["items"]]

            if response["metadata"]["next"]:
                cursor["page[from]"] = response["metadata"]["next"]
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
        payload: Dict[str, Any] = {"filter": {"dataset_item_ids": [item.id for item in items]}}
        self.client.archive_item(self.slug, self.team, payload)

    def restore_archived(self, items: Iterator[DatasetItem]) -> None:
        """
        Restores the archived ``DatasetItem``\\s that belong to this ``RemoteDataset``.

        Parameters
        ----------
        items : Iterator[DatasetItem]
            The ``DatasetItem``\\s to be restored.
        """
        payload: Dict[str, Any] = {"filter": {"dataset_item_ids": [item.id for item in items]}}
        self.client.restore_archived_item(self.slug, self.team, payload)

    def move_to_new(self, items: Iterator[DatasetItem]) -> None:
        """
        Changes the given ``DatasetItem``\\s status to ``new``.

        Parameters
        ----------
        items : Iterator[DatasetItem]
            The ``DatasetItem``\\s whose status will change.
        """
        payload: Dict[str, Any] = {"filter": {"dataset_item_ids": [item.id for item in items]}}
        self.client.move_item_to_new(self.slug, self.team, payload)

    def reset(self, items: Iterator[DatasetItem]) -> None:
        """
        Resets the given ``DatasetItem``\\s.

        Parameters
        ----------
        items : Iterator[DatasetItem]
            The ``DatasetItem``\\s to be resetted.
        """
        payload: Dict[str, Any] = {"filter": {"dataset_item_ids": [item.id for item in items]}}
        self.client.reset_item(self.slug, self.team, payload)

    def complete(self, items: Iterator[DatasetItem]) -> None:
        """
        Completes the given ``DatasetItem``\\s.

        Parameters
        ----------
        items : Iterator[DatasetItem]
            The ``DatasetItem``\\s to be completed.
        """
        wf_template_id_mapper = lambda item: item.current_workflow["workflow_template_id"]
        input_items: List[DatasetItem] = list(items)

        # We split into items with and without workflow
        items_wf = filter(lambda item: item.current_workflow, input_items)
        items_no_wf = filter(lambda item: item.current_workflow is None, input_items)

        # All items without workflow get instantiated
        items_instantiated: List[DatasetItem] = []
        for old_item in items_no_wf:
            (_, item) = self.client.instantiate_item(old_item.id, include_metadata=True)
            items_instantiated.append(item)

        #  We create new list of items from instantiated items and other items with workflow
        # We also group them by workflow_template_id, because we can't do batch across diff templates
        items = sorted([*items_wf, *items_instantiated], key=wf_template_id_mapper)
        items_by_wf_template = itertools.groupby(
            items,
            key=wf_template_id_mapper,
        )

        # For each WF template, we find complete stage template id
        # and try to set stage for all items in this workflow
        for wf_template_id, current_items in items_by_wf_template:
            current_items = list(current_items)
            sample_item = current_items[0]
            deep_sample_stages = sample_item.current_workflow["stages"].values()
            sample_stages = [item for sublist in deep_sample_stages for item in sublist]
            complete_stage = list(filter(lambda stage: stage["type"] == "complete", sample_stages))[0]

            filters = {"dataset_item_ids": [item.id for item in current_items]}
            try:
                self.client.move_to_stage(self.slug, self.team, filters, complete_stage["workflow_stage_template_id"])
            except ValidationError:
                raise ValueError("Unable to complete some of provided items. Make sure to assign them to a user first.")

    def delete_items(self, items: Iterator[DatasetItem]) -> None:
        """
        Deletes the given ``DatasetItem``\\s.

        Parameters
        ----------
        items : Iterator[DatasetItem]
            The ``DatasetItem``\\s to be deleted.
        """
        payload: Dict[str, Any] = {"filter": {"dataset_item_ids": [item.id for item in items]}}
        self.client.delete_item(self.slug, self.team, payload)

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
        if annotation_class_ids is None:
            annotation_class_ids = []

        payload = {
            "annotation_class_ids": annotation_class_ids,
            "name": name,
            "include_export_token": include_url_token,
            "include_authorship": include_authorship,
        }
        self.client.create_export(self.dataset_id, payload, self.team)

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
        return urljoin(self.client.base_url, f"/workview?dataset={self.dataset_id}&image={item.seq}")

    def post_comment(self, item: DatasetItem, text: str, x: float, y: float, w: float, h: float):
        """
        Adds a comment to an item in this dataset
        Instantiates a workflow if needed
        """
        maybe_workflow_id: Optional[int] = item.current_workflow_id

        if maybe_workflow_id is None:
            workflow_id: int = self.client.instantiate_item(item.id)
        else:
            workflow_id = maybe_workflow_id

        self.client.post_workflow_comment(workflow_id, text, x, y, w, h)

    def import_annotation(self, item_id: ItemId, payload: Dict[str, Any]) -> None:
        """
        Imports the annotation for the item with the given id.

        Parameters
        ----------
        item_id: ItemId
            Identifier of the Image or Video that we are import the annotation to.
        payload: Dict[str, Any]
            A dictionary with the annotation to import. The default format is:
            `{"annotations": serialized_annotations, "overwrite": "false"}`
        """

        self.client.import_annotation(item_id, payload=payload)
