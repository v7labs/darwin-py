import json
import tempfile
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)
from uuid import uuid4

from pydantic import ValidationError
from darwin.dataset import RemoteDataset
from darwin.dataset.release import Release
from darwin.dataset.storage_uploader import upload_artifacts
from darwin.dataset.upload_manager import (
    FileUploadCallback,
    ItemMergeMode,
    LocalFile,
    MultiFileItem,
    ProgressCallback,
    UploadHandler,
    UploadHandlerV2,
)
from darwin.dataset.utils import (
    chunk_items,
    get_external_file_name,
    get_external_file_type,
    is_relative_to,
    parse_external_file_path,
)
from darwin.datatypes import (
    AnnotationFile,
    ItemId,
    ObjectStore,
    PathLike,
    StorageKeyDictModel,
    StorageKeyListModel,
)
from darwin.exceptions import NotFound, UnknownExportVersion
from darwin.exporter.formats.darwin import build_image_annotation
from darwin.extractor.video import extract_artifacts
from darwin.item import DatasetItem
from darwin.item_sorter import ItemSorter
from darwin.utils import (
    AS_FRAMES_KEY,
    EXTRACT_VIEWS_KEY,
    NATIVE_VIDEO_EXTENSIONS,
    PRESERVE_FOLDERS_KEY,
    SUPPORTED_EXTENSIONS,
    find_files,
    urljoin,
)

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

    def get_releases(self, include_unavailable: bool = False) -> List["Release"]:
        """
        Get a sorted list of releases with the most recent first.

        Parameters
        ----------
        include_unavailable : bool, default: False
            If True, return  all releases, including those that are not available.

        Returns
        -------
        List["Release"]
            Returns a sorted list of available ``Release``\\s with the most recent first.
        """
        try:
            releases_json: List[Dict[str, Any]] = self.client.api_v2.get_exports(
                self.slug, team_slug=self.team
            )
        except NotFound:
            return []

        releases = [
            Release.parse_json(self.slug, self.team, payload)
            for payload in releases_json
        ]

        return sorted(
            (
                releases
                if include_unavailable
                else filter(lambda x: x.available, releases)
            ),
            key=lambda x: x.version,
            reverse=True,
        )

    def push(
        self,
        files_to_upload: Optional[Sequence[Union[PathLike, LocalFile]]],
        *,
        blocking: bool = True,
        multi_threaded: bool = True,
        max_workers: Optional[int] = None,
        fps: int = 0,
        as_frames: bool = False,
        extract_views: bool = False,
        handle_as_slices: Optional[bool] = False,
        files_to_exclude: Optional[List[PathLike]] = None,
        path: Optional[str] = None,
        preserve_folders: bool = False,
        progress_callback: Optional[ProgressCallback] = None,
        file_upload_callback: Optional[FileUploadCallback] = None,
        item_merge_mode: Optional[str] = None,
    ) -> UploadHandler:
        """
        Uploads a local dataset (images ONLY) in the datasets directory.

        Parameters
        ----------
        files_to_upload : Optional[List[Union[PathLike, LocalFile]]]
            List of files to upload. These can be folders.
            If `item_merge_mode` is set, these paths must be folders.
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
        handle_as_slices: Optioonal[bool], default: False
            Whether to upload DICOM files as slices
        files_to_exclude : Optional[PathLike]], default: None
            Optional list of files to exclude from the file scan. These can be folders.
        path: Optional[str], default: None
            Optional path to store the files in.
        preserve_folders : bool, default: False
            Specify whether or not to preserve folder paths when uploading
        progress_callback: Optional[ProgressCallback], default: None
            Optional callback, called every time the progress of an uploading files is reported.
        file_upload_callback: Optional[FileUploadCallback], default: None
            Optional callback, called every time a file chunk is uploaded.
        item_merge_mode : Optional[str]
            If set, each file path passed to `files_to_upload` behaves as follows:
            - Paths pointing directly to individual files are ignored
            - Paths pointing to folders of files will be uploaded according to the following mode rules.
            Note that folders will not be recursively searched, so only files in the first level of the folder will be uploaded:
                - "slots": Each file in the folder will be uploaded to a different slot of the same item.
                - "series": All `.dcm` files in the folder will be concatenated into a single slot. All other files are ignored.
                - "channels": Each file in the folder will be uploaded to a different channel of the same item.
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
        merge_incompatible_args = {
            PRESERVE_FOLDERS_KEY: preserve_folders,
            AS_FRAMES_KEY: as_frames,
            EXTRACT_VIEWS_KEY: extract_views,
        }

        if files_to_exclude is None:
            files_to_exclude = []

        if files_to_upload is None:
            raise ValueError("No files or directory specified.")

        if item_merge_mode:
            try:
                ItemMergeMode(item_merge_mode)
            except ValueError:
                raise ValueError(
                    f"Invalid item merge mode: {item_merge_mode}. Valid options are: 'slots', 'series', 'channels'"
                )
            incompatible_args = [
                arg for arg, value in merge_incompatible_args.items() if value
            ]

            if incompatible_args:
                incompatible_args_str = ", ".join(incompatible_args)
                raise TypeError(
                    f"`item_merge_mode` does not support the following incompatible arguments: {incompatible_args_str}."
                )

        # Folder paths
        search_files = [
            item for item in files_to_upload if not isinstance(item, LocalFile)
        ]

        if item_merge_mode:
            local_files, multi_file_items = _find_files_to_upload_as_multi_file_items(
                search_files, files_to_exclude, fps, item_merge_mode
            )
            handler = UploadHandlerV2(
                self, local_files, multi_file_items, handle_as_slices=handle_as_slices
            )
        else:
            local_files = _find_files_to_upload_as_single_file_items(
                search_files,
                files_to_upload,
                files_to_exclude,
                path,
                fps,
                as_frames,
                extract_views,
                preserve_folders,
            )
            handler = UploadHandlerV2(
                self, local_files, handle_as_slices=handle_as_slices
            )
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
        self,
        filters: Optional[Dict[str, Union[str, List[str]]]] = None,
        sort: Optional[Union[str, ItemSorter]] = None,
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
            # Backward compatibility with V1 filter parameter
            if "filenames" in filters:
                filters["item_names"] = filters["filenames"]
                del filters["filenames"]

            for list_type in [
                "item_names",
                "statuses",
                "item_ids",
                "slot_types",
                "item_paths",
            ]:
                if list_type in filters:
                    if isinstance(filters[list_type], list):
                        for value in filters[list_type]:
                            post_filters.append(("{}[]".format(list_type), value))
                    else:
                        post_filters.append((list_type, str(filters[list_type])))

        if sort:
            item_sorter = ItemSorter.parse(sort)
            post_sort[f"sort[{item_sorter.field}]"] = item_sorter.direction.value
        cursor = {"page[size]": 500, "include_workflow_data": "true"}
        while True:
            query = post_filters + list(post_sort.items()) + list(cursor.items())
            response = self.client.api_v2.fetch_items(
                self.dataset_id, query, team_slug=self.team
            )
            yield from [
                DatasetItem.parse(item, dataset_slug=self.slug)
                for item in response["items"]
            ]

            if response["page"]["next"]:
                cursor["page[from]"] = response["page"]["next"]
            else:
                return

    def archive(self, items: Iterable[DatasetItem]) -> None:
        """
        Archives (soft-deletion) the given ``DatasetItem``\\s belonging to this ``RemoteDataset``.

        Parameters
        ----------
        items : Iterable[DatasetItem]
            The ``DatasetItem``\\s to be archived.
        """
        payload: Dict[str, Any] = {
            "filters": {
                "item_ids": [item.id for item in items],
                "dataset_ids": [self.dataset_id],
            }
        }
        self.client.api_v2.archive_items(payload, team_slug=self.team)

    def restore_archived(self, items: Iterable[DatasetItem]) -> None:
        """
        Restores the archived ``DatasetItem``\\s that belong to this ``RemoteDataset``.

        Parameters
        ----------
        items : Iterable[DatasetItem]
            The ``DatasetItem``\\s to be restored.
        """
        payload: Dict[str, Any] = {
            "filters": {
                "item_ids": [item.id for item in items],
                "dataset_ids": [self.dataset_id],
            }
        }
        self.client.api_v2.restore_archived_items(payload, team_slug=self.team)

    def move_to_new(self, items: Iterable[DatasetItem]) -> None:
        """
        Changes the given ``DatasetItem``\\s status to ``new``.

        Parameters
        ----------
        items : Iterable[DatasetItem]
            The ``DatasetItem``\\s whose status will change.
        """

        workflow_id, stages = self._fetch_stages("dataset")
        if not stages:
            raise ValueError("Dataset's workflow is missing a dataset stage")

        self.client.api_v2.move_to_stage(
            {"item_ids": [item.id for item in items], "dataset_ids": [self.dataset_id]},
            stages[0]["id"],
            workflow_id,
            team_slug=self.team,
        )

    def complete(self, items: Iterable[DatasetItem]) -> None:
        """
        Completes the given ``DatasetItem``\\s.

        Parameters
        ----------
        items : Iterable[DatasetItem]
            The ``DatasetItem``\\s to be completed.
        """
        workflow_id, stages = self._fetch_stages("complete")
        if not stages:
            raise ValueError("Dataset's workflow is missing a complete stage")

        self.client.api_v2.move_to_stage(
            {"item_ids": [item.id for item in items], "dataset_ids": [self.dataset_id]},
            stages[0]["id"],
            workflow_id,
            team_slug=self.team,
        )

    def delete_items(self, items: Iterable[DatasetItem]) -> None:
        """
        Deletes the given ``DatasetItem``\\s.

        Parameters
        ----------
        items : Iterable[DatasetItem]
            The ``DatasetItem``\\s to be deleted.
        """
        self.client.api_v2.delete_items(
            {"dataset_ids": [self.dataset_id], "item_ids": [item.id for item in items]},
            team_slug=self.team,
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
        elif version is None:
            format = None
        else:
            raise UnknownExportVersion(version)

        filters = (
            None
            if not annotation_class_ids
            else {"annotation_class_ids": list(map(int, annotation_class_ids))}
        )

        self.client.api_v2.export_dataset(
            format=format,
            name=name,
            include_authorship=include_authorship,
            include_token=include_url_token,
            annotation_class_ids=None,
            filters=filters,
            dataset_slug=self.slug,
            team_slug=self.team,
        )

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
        return urljoin(
            self.client.base_url, f"/workview?dataset={self.dataset_id}&item={item.id}"
        )

    def post_comment(
        self,
        item: DatasetItem,
        text: str,
        x: float,
        y: float,
        w: float,
        h: float,
        slot_name: Optional[str] = None,
    ):
        """
        Adds a comment to an item in this dataset,
        Tries to infer slot_name if left out.
        """
        if not slot_name:
            if len(item.slots) != 1:
                raise ValueError(
                    f"Unable to infer slot for '{item.id}', has multiple slots: {','.join(item.slots)}"
                )
            slot_name = item.slots[0]["slot_name"]

        self.client.api_v2.post_comment(
            item.id, text, x, y, w, h, slot_name, team_slug=self.team
        )

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

        self.client.api_v2.import_annotation(
            item_id, payload=payload, team_slug=self.team
        )

    def _fetch_stages(self, stage_type):
        detailed_dataset = self.client.api_v2.get_dataset(self.dataset_id)
        workflow_ids = detailed_dataset["workflow_ids"]
        if len(workflow_ids) == 0:
            raise ValueError("Dataset is not part of a workflow")
        # currently we can only be part of one workflow
        workflow_id = workflow_ids[0]
        workflow = self.client.api_v2.get_workflow(workflow_id, team_slug=self.team)
        return (
            workflow_id,
            [stage for stage in workflow["stages"] if stage["type"] == stage_type],
        )

    def _build_image_annotation(
        self, annotation_file: AnnotationFile, team_name: str
    ) -> Dict[str, Any]:
        return build_image_annotation(annotation_file, team_name)

    def register(
        self,
        object_store: ObjectStore,
        storage_keys: Union[List[str], Dict[str, List[str]]],
        fps: Optional[Union[str, float]] = None,
        multi_planar_view: bool = False,
        preserve_folders: bool = False,
        multi_slotted: bool = False,
    ) -> Dict[str, List[str]]:
        """
        Register files from external storage in a Darwin dataset.

        Parameters
        ----------
        object_store : ObjectStore
            Object store to use for the registration.
        storage_keys : List[str] | Dict[str, List[str]]
            Either:
            - Single-slotted items: A list of storage keys
            - Multi-slotted items: A dictionary with keys as item names and values as lists of storage keys
        fps : Optional[str], default: None
            When the uploading file is a video, specify its framerate.
        multi_planar_view : bool, default: False
            Uses multiplanar view when uploading files.
        preserve_folders : bool, default: False
            Specify whether or not to preserve folder paths when uploading.
        multi_slotted : bool, default: False
            Specify whether the items are multi-slotted or not.

        Returns
        -------
        Dict[str, List[str]]
            A dictionary with the list of registered files.

        Raises
        ------
        ValueError
            If the type of ``storage_keys``:
            - Isn't List[str] when ``multi_slotted`` is False.
            - Isn't Dict[str, List[str]] when ``multi_slotted`` is True.
        """
        if multi_slotted:
            try:
                StorageKeyDictModel(storage_keys=storage_keys)  # type: ignore
            except ValidationError as e:
                print(
                    f"Error validating storage keys: {e}\n\nPlease make sure your storage keys are a list of strings"
                )
                raise e
            results = self.register_multi_slotted(
                object_store,
                storage_keys,  # type: ignore
                fps,
                multi_planar_view,
                preserve_folders,
            )
            return results
        else:
            try:
                StorageKeyListModel(storage_keys=storage_keys)  # type: ignore
            except ValidationError as e:
                print(
                    f"Error validating storage keys: {e}\n\nPlease make sure your storage keys are a dictionary with keys as item names and values as lists of storage keys"
                )
                raise e
            results = self.register_single_slotted(
                object_store,
                storage_keys,  # type: ignore
                fps,
                multi_planar_view,
                preserve_folders,
            )
            return results

    def register_locally_processed(
        self,
        object_store: ObjectStore,
        files: Union[List[Union[str, Path]], Dict[str, List[Union[str, Path]]]],
        path: str = "/",
        fps: float = 0.0,
        segment_length: int = 2,
        repair: bool = False,
        multi_slotted: bool = False,
        extract_preview_frames: bool = True,
        primary_frames_quality: int = 1,
    ) -> Dict[str, List[str]]:
        """
        Register locally preprocessed files to Darwin dataset using external storage.

        This function processes local files (extracting HLS artifacts, thumbnails, etc.),
        uploads them to the configured external storage, and registers them with Darwin.
        Files are preprocessed locally rather than on Darwin's servers.

        Parameters
        ----------
        object_store : ObjectStore
            Readonly external storage configuration.
            Get via: client.get_external_storage() with appropriate provider credentials.
        files : List[Union[str, Path]] | Dict[str, List[Union[str, Path]]]
            Either:
            - Single-slotted items: A list of video file paths (one item per video)
            - Multi-slotted items: A dictionary with keys as item names and values
              as lists of video file paths (multiple slots per item)
        path : str, default: "/"
            Path in dataset where items will be stored.
        fps : float, default: 0.0
            Target FPS for frame extraction. 0.0 means native fps.
        segment_length : int, default: 2
            HLS segment length in seconds.
        repair : bool, default: False
            Attempt video repair if errors are detected.
        multi_slotted : bool, default: False
            Specify whether the items are multi-slotted or not.
        extract_preview_frames : bool, default: True
            If True, extract preview frames for playback scrubbing.
            If False, skip extraction (system will use video segments for preview).
        primary_frames_quality : Optional[int], default: 1
            Quality setting for primary display frames.
            1 (default) means use PNG format (lossless).
            2-31 means use JPEG with that quality (2=best, 31=worst).

        Returns
        -------
        Dict[str, List[str]]
            A dictionary with the list of registered and blocked files:
            {
                "registered": ["Item video1.mp4 registered with ID 123", ...],
                "blocked": ["Item video2.mp4 blocked: duplicate", ...]
            }

        Raises
        ------
        ValueError
            If the type of ``files``:
            - Isn't List when ``multi_slotted`` is False.
            - Isn't Dict when ``multi_slotted`` is True.
            If any file does not have a supported extension.

        Example
        -------
        ```python
        storage = client.get_external_storage(
            team_slug="my-team",
            name="my-readonly-storage",
        )

        # Single-slotted: one item per video
        results = dataset.register_locally_processed(
            object_store=storage,
            files=["video1.mp4", "video2.mp4"],
            path="/recordings",
            fps=1.0
        )

        # Multi-slotted: multiple videos per item
        results = dataset.register_locally_processed(
            object_store=storage,
            files={
                "scene_1": ["front.mp4", "back.mp4"],
                "scene_2": ["camera1.mp4", "camera2.mp4"],
            },
            path="/scenes",
            fps=1.0,
            multi_slotted=True
        )

        # Skip preview frames and use JPEG for primary frames
        results = dataset.register_locally_processed(
            object_store=storage,
            files=["video.mp4"],
            extract_preview_frames=False,
            primary_frames_quality=5  # High quality JPEG
        )
        ```
        """
        if multi_slotted:
            if not isinstance(files, dict):
                raise ValueError(
                    "files must be a dictionary when multi_slotted=True. "
                    "Example: {'item_name': ['video1.mp4', 'video2.mp4']}"
                )
            for file_list in files.values():
                self._validate_supported_file_extensions(file_list)
            results = self.register_multi_slotted_readonly_videos(
                object_store=object_store,
                video_files=files,  # type: ignore
                path=path,
                fps=fps,
                segment_length=segment_length,
                repair=repair,
                extract_preview_frames=extract_preview_frames,
                primary_frames_quality=primary_frames_quality,
            )
        else:
            if not isinstance(files, list):
                raise ValueError(
                    "files must be a list when multi_slotted=False. "
                    "Example: ['video1.mp4', 'video2.mp4']"
                )
            self._validate_supported_file_extensions(files)
            results = self.register_single_slotted_readonly_videos(
                object_store=object_store,
                video_files=files,  # type: ignore
                path=path,
                fps=fps,
                segment_length=segment_length,
                repair=repair,
                extract_preview_frames=extract_preview_frames,
                primary_frames_quality=primary_frames_quality,
            )

        return results

    def _validate_supported_file_extensions(
        self,
        files: List[Union[str, Path]],
    ) -> None:
        """
        Validate that all provided files have supported file extensions.

        Currently only native video files are supported for local preprocessing.
        In the future, this method will be extended to support other file types.

        Parameters
        ----------
        files : List[Union[str, Path]]
            Files to validate

        Raises
        ------
        ValueError
            If any file does not have a supported extension.
        """
        for file_path in files:
            filename = str(file_path).lower()
            is_supported = any(
                filename.endswith(ext.lower()) for ext in NATIVE_VIDEO_EXTENSIONS
            )
            if not is_supported:
                raise ValueError(
                    f"The file '{file_path}' is not supported. "
                    f"Supported extensions: {', '.join(NATIVE_VIDEO_EXTENSIONS)}"
                )

    def register_single_slotted(
        self,
        object_store: ObjectStore,
        storage_keys: List[str],
        fps: Optional[Union[str, float]] = None,
        multi_planar_view: bool = False,
        preserve_folders: bool = False,
    ) -> Dict[str, List[str]]:
        """
        Register files in the dataset in a single slot.

        Parameters
        ----------
        object_store : ObjectStore
            Object store to use for the registration.
        storage_keys : List[str]
            List of storage keys to register.
        fps : Optional[str], default: None
            When the uploading file is a video, specify its framerate.
        multi_planar_view : bool, default: False
            Uses multiplanar view when uploading files.
        preserve_folders : bool, default: False
            Specify whether or not to preserve folder paths when uploading

        Returns
        -------
        Dict[str, List[str]]
            A dictionary with the list of registered files.

        Raises
        ------
        TypeError
            If the file type of any storage keyis not supported.
        """
        items = []
        for storage_key in storage_keys:
            file_type = get_external_file_type(storage_key)
            if not file_type:
                raise TypeError(
                    f"Unsupported file type for the following storage key: {storage_key}.\nPlease make sure your storage key ends with one of the supported extensions:\n{SUPPORTED_EXTENSIONS}"
                )
            item = {
                "path": parse_external_file_path(storage_key, preserve_folders),
                "type": file_type,
                "storage_key": storage_key,
                "name": (
                    storage_key.split("/")[-1] if "/" in storage_key else storage_key
                ),
            }
            if fps and file_type == "video":
                item["fps"] = fps
            if multi_planar_view and file_type == "dicom":
                item["extract_views"] = "true"
            items.append(item)

        # Do not register more than 10 items in a single request
        chunk_size = 10
        chunked_items = chunk_items(items, chunk_size)
        print(f"Registering {len(items)} items in chunks of {chunk_size} items...")
        results = {
            "registered": [],
            "blocked": [],
        }

        for chunk in chunked_items:
            payload = {
                "items": chunk,
                "dataset_slug": self.slug,
                "storage_slug": object_store.name,
            }
            print(f"Registering {len(chunk)} items...")
            response = self.client.api_v2.register_items(payload, team_slug=self.team)
            for item in json.loads(response.text)["items"]:
                item_info = f"Item {item['name']} registered with item ID {item['id']}"
                results["registered"].append(item_info)
            for item in json.loads(response.text)["blocked_items"]:
                item_info = f"Item {item['name']} was blocked for the reason: {item['slots'][0]['reason']}"
                results["blocked"].append(item_info)
        print(
            f"{len(results['registered'])} of {len(storage_keys)} items registered successfully"
        )
        if results["blocked"]:
            print("The following items were blocked:")
            for item in results["blocked"]:
                print(f"  - {item}")
        print(f"Reistration complete. Check your items in the dataset: {self.slug}")
        return results

    def register_multi_slotted(
        self,
        object_store: ObjectStore,
        storage_keys: Dict[str, List[str]],
        fps: Optional[Union[str, float]] = None,
        multi_planar_view: bool = False,
        preserve_folders: bool = False,
    ) -> Dict[str, List[str]]:
        """
        Register files in the dataset in multiple slots.

        Parameters
        ----------
        object_store : ObjectStore
            Object store to use for the registration.
        storage_keys : Dict[str, List[str]
            Storage keys to register. The keys are the item names and the values are lists of storage keys.
        fps : Optional[str], default: None
            When the uploading file is a video, specify its framerate.
        multi_planar_view : bool, default: False
            Uses multiplanar view when uploading files.
        preserve_folders : bool, default: False
            Specify whether or not to preserve folder paths when uploading

        Returns
        -------
        Dict[str, List[str]]
            A dictionary with the list of registered files.

        Raises
        ------
        TypeError
            If the file type of any storage key is not supported.
        """
        items = []
        for item in storage_keys:
            slots = []
            for storage_key in storage_keys[item]:
                file_name = get_external_file_name(storage_key)
                file_type = get_external_file_type(storage_key)
                if not file_type:
                    raise TypeError(
                        f"Unsupported file type for the following storage key: {storage_key}.\nPlease make sure your storage key ends with one of the supported extensions:\n{SUPPORTED_EXTENSIONS}"
                    )
                slot = {
                    "slot_name": file_name,
                    "type": file_type,
                    "storage_key": storage_key,
                    "file_name": file_name,
                }
                if fps and file_type == "video":
                    slot["fps"] = fps
                if multi_planar_view and file_type == "dicom":
                    slot["extract_views"] = "true"
                slots.append(slot)
            items.append(
                {
                    "slots": slots,
                    "name": item,
                    "path": parse_external_file_path(
                        storage_keys[item][0], preserve_folders
                    ),
                }
            )

        # Do not register more than 10 items in a single request
        chunk_size = 10
        chunked_items = chunk_items(items, chunk_size)
        print(f"Registering {len(items)} items in chunks of {chunk_size} items...")
        results = {
            "registered": [],
            "blocked": [],
        }

        for chunk in chunked_items:
            payload = {
                "items": chunk,
                "dataset_slug": self.slug,
                "storage_slug": object_store.name,
            }
            print(f"Registering {len(chunk)} items...")
            response = self.client.api_v2.register_items(payload, team_slug=self.team)
            for item in json.loads(response.text)["items"]:
                item_info = f"Item {item['name']} registered with item ID {item['id']}"
                results["registered"].append(item_info)
            for item in json.loads(response.text)["blocked_items"]:
                item_info = f"Item {item['name']} was blocked for the reason: {item['slots'][0]['reason']}"
                results["blocked"].append(item_info)
        print(
            f"{len(results['registered'])} of {len(storage_keys)} items registered successfully"
        )
        if results["blocked"]:
            print("The following items were blocked:")
            for item in results["blocked"]:
                print(f"  - {item}")
        print(f"Reistration complete. Check your items in the dataset: {self.slug}")
        return results

    def register_single_slotted_readonly_videos(
        self,
        object_store: ObjectStore,
        video_files: List[Union[str, Path]],
        path: str = "/",
        fps: float = 0.0,
        segment_length: int = 2,
        repair: bool = False,
        extract_preview_frames: bool = True,
        primary_frames_quality: int = 1,
    ) -> Dict[str, List[str]]:
        """
        Register videos as single-slotted items from readonly storage.
        Creates one item per video file.

        Parameters
        ----------
        object_store : ObjectStore
            Readonly external storage configuration.
            Get via: client.get_external_storage()
        video_files : List[Union[str, Path]]
            List of video file paths to register
        path : str
            Path in dataset where items will be stored (default "/")
        fps : float
            Target FPS for frame extraction (0.0 = native fps)
        segment_length : int
            HLS segment length in seconds
        repair : bool
            Attempt video repair if errors detected
        extract_preview_frames : bool, default: True
            If True, extract preview frames for playback scrubbing.
            If False, skip extraction (system will use video segments).
        primary_frames_quality : Optional[int], default: 1
            Quality setting for primary display frames.
            1 means use PNG format (lossless).
            2-31 means use JPEG with that quality (2=best, 31=worst).

        Returns
        -------
        Dict[str, List[str]]
            {
                "registered": ["Item video1.mp4 registered with ID 123", ...],
                "blocked": ["Item video2.mp4 blocked: duplicate", ...]
            }

        Example
        -------
        ```python
        storage = client.get_external_storage(
            team_slug="my-team",
            name="my-readonly-storage",
        )

        results = dataset.register_single_slotted_readonly_videos(
            object_store=storage,
            video_files=["video1.mp4", "video2.mp4"],
            path="/recordings",
            fps=1.0
        )
        ```
        """
        # Validation
        self._validate_object_store_provider(object_store)

        # Convert to Path objects and validate existence
        video_paths = [Path(vf) for vf in video_files]
        for video_path in video_paths:
            if not video_path.exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")

        items_to_register = []

        # Process each video as a separate item
        for video_path in video_paths:
            # Generate new UUIDs for each video
            item_uuid = str(uuid4())
            slot_uuid = str(uuid4())
            storage_key_prefix = self._build_storage_key_prefix(
                object_store, item_uuid, slot_uuid
            )

            # Extract, upload, and get metadata
            slot_metadata = self._process_video_file_for_readonly(
                video_path=video_path,
                object_store=object_store,
                storage_key_prefix=storage_key_prefix,
                fps=fps,
                segment_length=segment_length,
                repair=repair,
                extract_preview_frames=extract_preview_frames,
                primary_frames_quality=primary_frames_quality,
            )

            # Build item payload
            slot_dict = {
                "slot_name": video_path.name,
                "storage_key": f"{storage_key_prefix}/{video_path.name}",
                "file_name": video_path.name,
                **slot_metadata,
            }

            item_dict = {
                "name": video_path.name,
                "path": path,
                "slots": [slot_dict],
            }
            items_to_register.append(item_dict)

        # Submit registration
        return self._submit_readonly_registration(
            items_to_register=items_to_register,
            object_store=object_store,
        )

    def register_multi_slotted_readonly_videos(
        self,
        object_store: ObjectStore,
        video_files: Dict[str, List[Union[str, Path]]],
        path: str = "/",
        fps: float = 0.0,
        segment_length: int = 2,
        repair: bool = False,
        extract_preview_frames: bool = True,
        primary_frames_quality: int = 1,
    ) -> Dict[str, List[str]]:
        """
        Register videos as multi-slotted items from readonly storage.
        Creates one item per dictionary key, with multiple slots per item.
        Slot names are derived from filenames. If the same filename appears
        multiple times in an item, number suffixes are added (e.g., video.mp4,
        video.mp4_1, video.mp4_2).

        Parameters
        ----------
        object_store : ObjectStore
            Readonly external storage configuration
        video_files : Dict[str, List[Union[str, Path]]]
            Dictionary mapping item_name to list of video file paths.
            Each item gets multiple slots (one per video).
        path : str
            Path in dataset where items will be stored (default "/")
        fps : float
            Target FPS for frame extraction (0.0 = native fps)
        segment_length : int
            HLS segment length in seconds
        repair : bool
            Attempt video repair if errors detected
        extract_preview_frames : bool, default: True
            If True, extract preview frames for playback scrubbing.
            If False, skip extraction (system will use video segments).
        primary_frames_quality : Optional[int], default: 1
            Quality setting for primary display frames.
            1 means use PNG format (lossless).
            2-31 means use JPEG with that quality (2=best, 31=worst).

        Returns
        -------
        Dict[str, List[str]]
            Registration results

        Example
        -------
        ```python
        storage = client.get_external_storage(allow_readonly=True)

        results = dataset.register_multi_slotted_readonly_videos(
            object_store=storage,
            video_files={
                "multi_view_scene_1": ["videos/front.mp4", "videos/back.mp4"],
                "multi_view_scene_2": [
                    "videos/front.mp4",  # Will become slot "front.mp4"
                    "videos/back.mp4",   # Will become slot "back.mp4"
                    "other/front.mp4",   # Will become slot "front.mp4_1" (duplicate filename)
                ]
            },
            path="/recordings",
            fps=1.0
        )
        ```
        """
        # Validation
        self._validate_object_store_provider(object_store)

        # Convert to Path objects and validate existence
        video_paths_by_item = {}
        for item_name, video_list in video_files.items():
            video_paths_by_item[item_name] = [Path(vf) for vf in video_list]
            for video_path in video_paths_by_item[item_name]:
                if not video_path.exists():
                    raise FileNotFoundError(
                        f"Video file not found for item {item_name}: {video_path}"
                    )

        items_to_register = []

        for item_name, video_paths in video_paths_by_item.items():
            # Build slot name mapping with deduplication suffixes
            slot_name_counts = {}  # Track filename occurrences
            slot_info_list = []  # [(video_path, slot_name)]

            for video_path in video_paths:
                base_slot_name = video_path.name
                if base_slot_name not in slot_name_counts:
                    slot_name_counts[base_slot_name] = 0
                    slot_name = base_slot_name
                else:
                    slot_name_counts[base_slot_name] += 1
                    slot_name = f"{base_slot_name}_{slot_name_counts[base_slot_name]}"

                slot_info_list.append((video_path, slot_name))

            # Generate new item_uuid
            item_uuid = str(uuid4())

            # Build unique files map with slot UUIDs using absolute path as key
            unique_files = {}  # {absolute_path: (video_path, slot_uuid)}
            path_to_metadata = {}  # {absolute_path: metadata}

            for video_path, slot_name in slot_info_list:
                abs_path = str(video_path.absolute())

                if abs_path not in unique_files:
                    slot_uuid = str(uuid4())
                    unique_files[abs_path] = (video_path, slot_uuid)

            # Process each unique file
            for abs_path, (video_path, slot_uuid) in unique_files.items():
                storage_key_prefix = self._build_storage_key_prefix(
                    object_store, item_uuid, slot_uuid
                )
                slot_metadata = self._process_video_file_for_readonly(
                    video_path=video_path,
                    object_store=object_store,
                    storage_key_prefix=storage_key_prefix,
                    fps=fps,
                    segment_length=segment_length,
                    repair=repair,
                    extract_preview_frames=extract_preview_frames,
                    primary_frames_quality=primary_frames_quality,
                )
                path_to_metadata[abs_path] = slot_metadata

            # Build slots for this item
            slots = []
            for video_path, slot_name in slot_info_list:
                abs_path = str(video_path.absolute())
                _, slot_uuid = unique_files[abs_path]
                storage_key_prefix = self._build_storage_key_prefix(
                    object_store, item_uuid, slot_uuid
                )

                slot_dict = {
                    "slot_name": slot_name,
                    "storage_key": f"{storage_key_prefix}/{video_path.name}",
                    "file_name": video_path.name,
                    **path_to_metadata[abs_path],
                }
                slots.append(slot_dict)

            item_dict = {"name": item_name, "path": path, "slots": slots}
            items_to_register.append(item_dict)

        # Submit registration
        return self._submit_readonly_registration(
            items_to_register=items_to_register,
            object_store=object_store,
        )

    def _validate_object_store_provider(self, object_store: ObjectStore) -> None:
        """
        Validate object store provider for readonly video registration.

        Parameters
        ----------
        object_store : ObjectStore
            Storage configuration to validate

        Raises
        ------
        ValueError
            If provider is not supported
        """

        if object_store.provider not in ["aws", "gcp", "azure"]:
            raise ValueError(
                f"Unsupported storage provider: {object_store.provider}. "
                f"Supported providers: aws, gcp, azure"
            )

    def _build_storage_key_prefix(
        self, object_store: ObjectStore, item_uuid: str, slot_uuid: str
    ) -> str:
        """
        Build storage key prefix, handling None/empty prefix properly.

        For Azure, the container name is extracted separately during client creation,
        so we only use the path portion (after container/) in the storage key.

        Parameters
        ----------
        object_store : ObjectStore
            Storage configuration
        item_uuid : str
            UUID for the item
        slot_uuid : str
            UUID for the slot

        Returns
        -------
        str
            Storage key prefix (e.g., "prefix/item_uuid/files/slot_uuid" or
            "item_uuid/files/slot_uuid" if prefix is None/empty)
            For Azure: "path/item_uuid/files/slot_uuid" (without container name)
        """
        base_path = f"{item_uuid}/files/{slot_uuid}"

        # For Azure, extract only the path portion (not container)
        if object_store.provider == "azure":
            if not object_store.prefix or object_store.prefix.strip() == "":
                # Empty prefix - no path portion
                return base_path
            elif "/" in object_store.prefix:
                # Extract path portion after container: "container/path" -> "path"
                _, _, path_portion = object_store.prefix.partition("/")
                if path_portion:
                    return f"{path_portion}/{base_path}"
                return base_path
            else:
                # No slash: prefix is just container name, no path portion
                return base_path
        else:
            # For AWS/GCP, use full prefix as-is
            if object_store.prefix:
                return f"{object_store.prefix}/{base_path}"
            return base_path

    def _process_video_file_for_readonly(
        self,
        video_path: Path,
        object_store: ObjectStore,
        storage_key_prefix: str,
        fps: float,
        segment_length: int,
        repair: bool,
        extract_preview_frames: bool = True,
        primary_frames_quality: int = 1,
    ) -> Dict:
        """
        Process a single video file: extract artifacts, upload to storage.

        Parameters
        ----------
        video_path : Path
            Path to video file
        object_store : ObjectStore
            Storage configuration
        storage_key_prefix : str
            Storage key prefix for the artifacts
        fps : float
            Target FPS
        segment_length : int
            Segment length in seconds
        repair : bool
            Whether to repair video
        extract_preview_frames : bool, default: True
            If True, extract preview frames for playback scrubbing.
            If False, skip extraction (system will use video segments).
        primary_frames_quality : Optional[int], default: 1
            Quality setting for primary display frames.
            1 means use PNG format (lossless).
            2-31 means use JPEG with that quality (2=best, 31=worst).

        Returns
        -------
        Dict
            Slot metadata from registration payload
        """
        with tempfile.TemporaryDirectory(prefix="darwin_video_") as tmp_dir:
            artifacts_dir = Path(tmp_dir)

            # Extract artifacts
            print(f"\nExtracting artifacts for {video_path.name}...")
            extract_artifacts(
                source_file=str(video_path),
                output_dir=str(artifacts_dir),
                storage_key_prefix=storage_key_prefix,
                fps=fps,
                segment_length=segment_length,
                repair=repair,
                save_metadata=True,
                extract_preview_frames=extract_preview_frames,
                primary_frames_quality=primary_frames_quality,
            )

            # Upload to storage
            print(f"\nUploading artifacts for {video_path.name}...")
            upload_artifacts(
                object_store=object_store,
                local_artifacts_dir=str(artifacts_dir),
                source_file=str(video_path),
                storage_key_prefix=storage_key_prefix,
            )

            # Load metadata before temp directory is cleaned up
            metadata_file = artifacts_dir / "metadata.json"
            with open(metadata_file, "r") as f:
                metadata = json.load(f)

            registration_payload = metadata["registration_payload"]
            return self._extract_slot_metadata(registration_payload)

    def _submit_readonly_registration(
        self,
        items_to_register: List[Dict],
        object_store: ObjectStore,
    ) -> Dict[str, List[str]]:
        """
        Submit readonly registration to Darwin.

        Parameters
        ----------
        items_to_register : List[Dict]
            List of item dictionaries to register
        object_store : ObjectStore
            Storage configuration

        Returns
        -------
        Dict[str, List[str]]
            Registration results with registered and blocked items
        """
        results = {"registered": [], "blocked": []}

        # Register in chunks of 10
        chunk_size = 10
        chunked_items = chunk_items(items_to_register, chunk_size)
        print(
            f"Registering {len(items_to_register)} items in chunks of {chunk_size}..."
        )

        for chunk in chunked_items:
            payload = {
                "items": chunk,
                "dataset_slug": self.slug,
                "storage_slug": object_store.name,
            }

            response = self.client.api_v2.register_readonly_items(
                payload=payload, team_slug=self.team
            )

            for item in response.get("items", []):
                results["registered"].append(
                    f"Item {item['name']} registered with item ID {item['id']}"
                )

            for item in response.get("blocked_items", []):
                slots = item.get("slots", [])
                reason = slots[0].get("reason", "unknown") if slots else "unknown"
                results["blocked"].append(f"Item {item['name']} was blocked: {reason}")

        # Print results
        print(
            f"{len(results['registered'])} of {len(items_to_register)} items registered successfully"
        )
        if results["blocked"]:
            print("The following items were blocked:")
            for item in results["blocked"]:
                print(f"  - {item}")

        return results

    def _extract_slot_metadata(self, registration_payload: Dict) -> Dict:
        """
        Extract slot-specific metadata from registration payload.

        Transforms the payload from `darwin/extractor/video.py` into the format
        expected by the Darwin backend's `register_existing_readonly` endpoint.

        Parameters
        ----------
        registration_payload : Dict
            Full registration payload from extract_artifacts

        Returns
        -------
        Dict
            Slot-specific metadata fields

        Notes
        -----
        Dispatches to type-specific extraction methods:
        - Videos: `_extract_video_slot_metadata()` -> ReadOnlyVideoSlot schema
        - Images: `_extract_image_slot_metadata()` -> ReadOnlyImageSlot schema
        """
        if registration_payload.get("type") == "video":
            return self._extract_video_slot_metadata(registration_payload)
        return self._extract_image_slot_metadata(registration_payload)

    def _extract_video_slot_metadata(self, registration_payload: Dict) -> Dict:
        """
        Extract video slot metadata for ReadOnlyVideoSlot schema.

        The ReadOnlyVideoSlot schema uses root-level video fields (width, height,
        native_fps, visible_frames, total_frames, hls_segments, etc.) for a compact
        payload that doesn't grow with frame count.

        Parameters
        ----------
        registration_payload : Dict
            Full registration payload from video extractor

        Returns
        -------
        Dict
            Video slot metadata conforming to ReadOnlyVideoSlot schema

        Notes
        -----
        The extractor generates some fields that are NOT valid for ReadOnlyVideoSlot:
        - `fps`: Use `native_fps` only (fps is for upload-based registration)
        - `as_frames`: Not in ReadOnlyVideoSlot schema
        """
        # Fields that belong to the item level, not the slot
        item_level_fields = {"name", "path"}

        # Fields that are INVALID for ReadOnlyVideoSlot but may be in extractor output
        invalid_fields = {
            "fps",  # Use native_fps only; fps is for upload-based registration
            "as_frames",  # Not in ReadOnlyVideoSlot schema
        }

        # Valid fields for ReadOnlyVideoSlot (videos with pre-processed HLS + frames)
        # Required: slot_name, file_name, storage_key, width, height, native_fps,
        #           visible_frames, total_frames, hls_segments, storage_sections_key_prefix,
        #           storage_thumbnail_key, storage_frames_manifest_key
        # Note: slot_name and file_name are provided by the caller when registering items.
        # Optional: storage_sections_key_extension (default: "png"),
        #           storage_low_quality_sections_key_prefix, storage_audio_peaks_key, size_bytes
        valid_fields = {
            "type",
            "slot_name",
            "file_name",
            "storage_key",
            "width",
            "height",
            "native_fps",
            "visible_frames",
            "total_frames",
            "hls_segments",
            "storage_sections_key_prefix",
            "storage_sections_key_extension",
            "storage_low_quality_sections_key_prefix",
            "storage_frames_manifest_key",
            "storage_thumbnail_key",
            "storage_audio_peaks_key",
            "size_bytes",
        }

        slot_payload: Dict[str, Any] = {}

        for k, v in registration_payload.items():
            if k in item_level_fields:
                continue
            if k in invalid_fields:
                continue

            # Rename total_size_bytes to size_bytes (extractor vs backend naming)
            key_to_write = "size_bytes" if k == "total_size_bytes" else k

            if key_to_write in valid_fields:
                slot_payload[key_to_write] = v

        return slot_payload

    def _extract_image_slot_metadata(self, registration_payload: Dict) -> Dict:
        """
        Extract image slot metadata for ReadOnlyImageSlot schema.

        Parameters
        ----------
        registration_payload : Dict
            Full registration payload for an image

        Returns
        -------
        Dict
            Image slot metadata conforming to ReadOnlyImageSlot schema

        Notes
        -----
        The `storage_key` field is CRITICAL for images - without it, the backend
        cannot locate the file on external storage, causing items to stay in
        "Processing" state and blocking annotation import.
        """
        # Fields that belong to the item level, not the slot
        item_level_fields = {"name", "path"}

        # Valid fields for ReadOnlyImageSlot
        # Required: slot_name, file_name, storage_key (to locate the file)
        # Note: slot_name and file_name are provided by the caller when registering items.
        # Optional: width, height, storage_thumbnail_key, size_bytes
        valid_fields = {
            "type",
            "slot_name",
            "file_name",
            "storage_key",  # CRITICAL: Required for backend to locate the file
            "width",
            "height",
            "storage_thumbnail_key",
            "size_bytes",
        }

        slot_payload: Dict[str, Any] = {}

        for k, v in registration_payload.items():
            if k in item_level_fields:
                continue

            # Rename total_size_bytes to size_bytes (extractor vs backend naming)
            key_to_write = "size_bytes" if k == "total_size_bytes" else k

            if key_to_write in valid_fields:
                slot_payload[key_to_write] = v

        return slot_payload


def _find_files_to_upload_as_multi_file_items(
    search_files: List[PathLike],
    files_to_exclude: List[PathLike],
    fps: int,
    item_merge_mode: str,
) -> Tuple[List[LocalFile], List[MultiFileItem]]:
    """
    Finds files to upload according to the `item_merge_mode`.
    Does not search each directory recursively, only considers files in the first level of each directory.

    Parameters
    ----------
    search_files : List[PathLike]
        List of directories to search for files.
    files_to_exclude : List[PathLike]
        List of files to exclude from the file scan.
    fps : int
        When uploading video files, specify the framerate
    item_merge_mode : str
        Mode to merge the files in the folders. Valid options are: 'slots', 'series', 'channels'.

    Returns
    -------
    List[LocalFile]
        List of `LocalFile` objects contained within each `MultiFileItem`
    List[MultiFileItem]
        List of `MultiFileItem` objects to be uploaded
    """
    multi_file_items, local_files = [], []
    for directory in search_files:
        files_in_directory = list(
            find_files(
                [directory],
                files_to_exclude=files_to_exclude,
                recursive=False,
                sort=True,
            )
        )
        if not files_in_directory:
            print(
                f"Warning: There are no files in the first level of {directory}, skipping directory"
            )
            continue
        multi_file_item = MultiFileItem(
            Path(directory), files_in_directory, ItemMergeMode(item_merge_mode), fps
        )
        multi_file_items.append(multi_file_item)
        local_files.extend(multi_file_item.files)

    if not multi_file_items:
        raise ValueError(
            "No valid folders to upload after searching the passed directories for files"
        )
    return local_files, multi_file_items


def _find_files_to_upload_as_single_file_items(
    search_files: List[PathLike],
    files_to_upload: Optional[Sequence[Union[PathLike, LocalFile]]],
    files_to_exclude: List[PathLike],
    path: Optional[str],
    fps: int,
    as_frames: bool,
    extract_views: bool,
    preserve_folders: bool,
) -> List[LocalFile]:
    """
    Finds files to upload as single-slotted dataset items. Recursively searches the passed directories for files.

    Parameters
    ----------
    search_files : List[PathLike]
        List of directories to search for files.

    files_to_exclude : Optional[List[PathLike]]
        List of files to exclude from the file scan.
    files_to_upload : Optional[List[Union[PathLike, LocalFile]]]
        List of files to upload. These can be folders.
    path : Optional[str]
        Path to store the files in.
    fps: int
        When uploading video files, specify the framerate.
    as_frames: bool
        When uploading video files, specify whether to upload as a list of frames.
    extract_views: bool
        When uploading volume files, specify whether to split into orthogonal views.
    preserve_folders: bool
        Specify whether or not to preserve folder paths when uploading.

    Returns
    -------
    List[LocalFile]
        List of files to upload.
    """
    # Direct file paths
    uploading_files = [item for item in files_to_upload if isinstance(item, LocalFile)]

    generic_parameters_specified = (
        path is not None or fps != 0 or as_frames is not False
    )

    if (
        any(isinstance(item, LocalFile) for item in uploading_files)
        and generic_parameters_specified
    ):
        raise ValueError("Cannot specify a path when uploading a LocalFile object.")

    for found_file in find_files(search_files, files_to_exclude=files_to_exclude):
        local_path = path
        if preserve_folders:
            source_files = [
                source_file
                for source_file in search_files
                if is_relative_to(found_file, source_file)
            ]
            if source_files:
                local_path = str(
                    found_file.relative_to(source_files[0]).parent.as_posix()
                )
                if local_path == ".":
                    local_path = "/"
        uploading_files.append(
            LocalFile(
                found_file,
                fps=fps,
                as_frames=as_frames,
                extract_views=extract_views,
                path=local_path,
            )
        )

    if not uploading_files:
        raise ValueError(
            "No files to upload, check your path, exclusion filters and resume flag"
        )

    return uploading_files
