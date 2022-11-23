import concurrent.futures
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    BinaryIO,
    Callable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
)

import requests

from darwin.datatypes import PathLike
from darwin.doc_enum import DocEnum
from darwin.path_utils import construct_full_path
from darwin.utils import chunk

if TYPE_CHECKING:
    from darwin.client import Client
    from darwin.dataset import RemoteDataset
    from darwin.dataset.identifier import DatasetIdentifier

from abc import ABC, abstractmethod
from typing import Dict


class ItemPayload:
    """
    Represents an item's payload.

    Parameters
    ----------
    dataset_item_id : int
        The id of the dataset this item belongs to.
    filename : str
        The filename of where this ``ItemPayload``'s data is.
    path : str
        The path to ``filename``.
    reason : Optional[str], default: None
        A reason to upload this ``ItemPayload``.

    Attributes
    ----------
    dataset_item_id : int
        The id of the dataset this item belongs to.
    filename : str
        The filename of where this ``ItemPayload``'s data is.
    path : str
        The path to ``filename``.
    reason : Optional[str], default: None
        A reason to upload this ``ItemPayload``.
    """

    def __init__(
        self,
        *,
        dataset_item_id: int,
        filename: str,
        path: str,
        reason: Optional[str] = None,
        slots: Optional[any] = None,
    ):
        self.dataset_item_id = dataset_item_id
        self.filename = filename
        self.path = path
        self.reason = reason
        self.slots = slots

    @staticmethod
    def parse_v2(payload):
        if len(payload["slots"]) > 1:
            raise NotImplemented("multiple files support not yet implemented")
        slot = payload["slots"][0]
        return ItemPayload(
            dataset_item_id=payload.get("id", None),
            filename=payload["name"],
            path=payload["path"],
            reason=slot.get("reason", None),
            slots=payload["slots"],
        )

    @property
    def full_path(self) -> str:
        """The full ``Path`` (with filename inclduded) to the file."""
        return construct_full_path(self.path, self.filename)


class UploadStage(DocEnum):
    """
    The different stages of uploading a file.
    """

    REQUEST_SIGNATURE = 0, "First stage, when authentication is being performed."
    UPLOAD_TO_S3 = 1, "Second stage, when the file is being uploaded to S3."
    CONFIRM_UPLOAD_COMPLETE = 2, "Final stage, when we confirm the file was correctly uploaded."
    OTHER = 3, "If the stage of the upload process is unknown."


@dataclass
class UploadRequestError(Exception):
    """
    Error throw when uploading a file fails with an unrecoverable error.
    """

    #: The ``Path`` of the file being uploaded.
    file_path: Path

    #: The ``UploadStage`` when the  failure happened.
    stage: UploadStage

    #: The ``Exception`` that triggered this unrecoverable error.
    error: Optional[Exception] = None


class LocalFile:
    """
    Represents a file locally stored.

    Parameters
    ----------
    local_path : PathLike
        The ``Path`` of the file.
    kwargs : Any
        Data relative to this file. Can be anything.

    Attributes
    ----------
    local_path : PathLike
        The ``Path`` of the file.
    data : Dict[str, str]
        Dictionary with metadata relative to this file. It has the following format:

        .. code-block:: python

            {
                "filename": "a_filename",
                "path": "a path"
            }

        - ``data["filename"]`` will hold the value passed as ``filename`` from ``kwargs`` or default to ``self.local_path.name``
        - ``data["path"]`` will hold the value passed as ``path`` from ``kwargs`` or default to ``"/"``

    """

    def __init__(self, local_path: PathLike, **kwargs):
        self.local_path = Path(local_path)
        self.data = kwargs
        self._type_check(kwargs)

    def _type_check(self, args) -> None:
        self.data["filename"] = args.get("filename") or self.local_path.name
        self.data["path"] = args.get("path") or "/"

    def serialize(self):
        return {"files": [{"file_name": self.data["filename"], "slot_name": "0"}], "name": self.data["filename"]}

    def serialize_v2(self):
        optional_properties = ["tags", "fps", "as_frames", "extract_views"]
        slot = {"file_name": self.data["filename"], "slot_name": "0"}
        for optional_property in optional_properties:
            if optional_property in self.data:
                slot[optional_property] = self.data.get(optional_property)

        return {
            "slots": [slot],
            "name": self.data["filename"],
            "path": self.data["path"],
        }

    @property
    def full_path(self) -> str:
        """The full ``Path`` (with filename inclduded) to the file."""
        return construct_full_path(self.data["path"], self.data["filename"])


class FileMonitor(object):
    """
    Monitors the progress of a :class:``BufferedReader``.

    To use this monitor, you construct your :class:``BufferedReader`` as you
    normally would, then construct this object with it as argument.

    Parameters
    ----------
    io : BinaryIO
        IO object used by this class. Depency injection.
    file_size : int
        The fie of the file in bytes.
    callback : Callable[["FileMonitor"], None]
        Callable function used by this class. Depency injection via constructor.

    Attributes
    ----------
    io : BinaryIO
        IO object used by this class. Depency injection.
    callback : Callable[["FileMonitor"], None]
        Callable function used by this class. Depency injection.
    bytes_read : int
      Amount of bytes read from the IO.
    len : int
        Total size of the IO.
    """

    def __init__(self, io: BinaryIO, file_size: int, callback: Callable[["FileMonitor"], None]):
        self.io: BinaryIO = io
        self.callback: Callable[["FileMonitor"], None] = callback

        self.bytes_read: int = 0
        self.len: int = file_size

    def read(self, size: int = -1) -> Any:
        """
        Reads given amount of bytes from configured IO and calls the configured callback for each
        block read. The callback is passed a reference this object that can be used to get current
        self.bytes_read.

        Parameters
        ----------
        size : int, default: -1
            The number of bytes to read. Defaults to -1, so all bytes until EOF are read.

        Returns
        -------
        data: Any
            Data read from the IO.
        """
        data: Any = self.io.read(size)
        self.bytes_read += len(data)
        self.callback(self)

        return data


ByteReadCallback = Callable[[Optional[str], float, float], None]
ProgressCallback = Callable[[int, float], None]
FileUploadCallback = Callable[[str, int, int], None]


class UploadHandler(ABC):
    """
    Holds responsabilities for file upload management and failure into ``RemoteDataset``\\s.

    Parameters
    ----------
    dataset: RemoteDataset
        Target ``RemoteDataset`` where we want to upload our files to.
    local_files : List[LocalFile]
        List of ``LocalFile``\\s to be uploaded.

    Attributes
    ----------
    dataset : RemoteDataset
        Target ``RemoteDataset`` where we want to upload our files to..
    errors : List[UploadRequestError]
        List of errors that happened during the upload process.
    local_files : List[LocalFile]
        List of ``LocalFile``\\s to be uploaded.
    blocked_items : List[ItemPayload]
        List of items that were not able to be uploaded.
    pending_items : List[ItemPayload]
        List of items waiting to be uploaded.
    """

    def __init__(self, dataset: "RemoteDataset", local_files: List[LocalFile]):
        self.dataset: RemoteDataset = dataset
        self.errors: List[UploadRequestError] = []
        self.local_files: List[LocalFile] = local_files
        self._progress: Optional[Iterator[Callable[[Optional[ByteReadCallback]], None]]] = None

        self.blocked_items, self.pending_items = self._request_upload()

    @staticmethod
    def build(dataset: "RemoteDataset", local_files: List[LocalFile]):
        if dataset.version == 1:
            return UploadHandlerV1(dataset, local_files)
        elif dataset.version == 2:
            return UploadHandlerV2(dataset, local_files)
        else:
            raise ValueError(f"Unsupported dataset version: {dataset.version}")

    @property
    def client(self) -> "Client":
        """The ``Client`` used by this ``UploadHander``\\'s ``RemoteDataset``."""
        return self.dataset.client

    @property
    def dataset_identifier(self) -> "DatasetIdentifier":
        """The ``DatasetIdentifier`` of this ``UploadHander``\\'s ``RemoteDataset``."""
        return self.dataset.identifier

    @property
    def blocked_count(self) -> int:
        """Number of items that could not be uploaded successfully."""
        return len(self.blocked_items)

    @property
    def error_count(self) -> int:
        """Number of errors that prevented items from being uploaded."""
        return len(self.errors)

    @property
    def pending_count(self) -> int:
        """Number of items waiting to be uploaded."""
        return len(self.pending_items)

    @property
    def total_count(self) -> int:
        """Total number of blocked and pending items."""
        return self.pending_count + self.blocked_count

    @property
    def progress(self):
        """Current level of upload progress."""
        return self._progress

    def prepare_upload(self) -> Optional[Iterator[Callable[[Optional[ByteReadCallback]], None]]]:
        self._progress = self._upload_files()
        return self._progress

    def upload(
        self,
        multi_threaded: bool = True,
        progress_callback: Optional[ProgressCallback] = None,
        file_upload_callback: Optional[FileUploadCallback] = None,
        max_workers: Optional[int] = None,
    ) -> None:
        if not self._progress:
            self.prepare_upload()

        if progress_callback:
            progress_callback(self.pending_count, 0)

        # needed to ensure that we don't mark a file as completed twice
        file_complete: Set[str] = set()

        def callback(file_name, file_total_bytes, file_bytes_sent):
            if file_upload_callback:
                file_upload_callback(file_name, file_total_bytes, file_bytes_sent)

            if progress_callback:
                if file_total_bytes == file_bytes_sent and file_name not in file_complete:
                    file_complete.add(file_name)
                    progress_callback(self.pending_count, 1)

        if max_workers:
            if max_workers < 1:
                raise ValueError("max_workers must be greater than 0")
            elif max_workers > concurrent.futures.ThreadPoolExecutor()._max_workers:
                raise ValueError(
                    f"max_workers must be less than or equal to {concurrent.futures.ThreadPoolExecutor()._max_workers}"
                )

        if multi_threaded and self.progress:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_progress = {executor.submit(f, callback) for f in self.progress}
                for future in concurrent.futures.as_completed(future_to_progress):
                    try:
                        future.result()
                    except Exception as exc:
                        print("exception", exc)
        elif self.progress:
            for file_to_upload in self.progress:
                file_to_upload(callback)

    @abstractmethod
    def _request_upload(self) -> Tuple[List[ItemPayload], List[ItemPayload]]:
        pass

    @abstractmethod
    def _upload_files(self) -> Iterator[Callable[[Optional[ByteReadCallback]], None]]:
        pass

    @abstractmethod
    def _upload_file(
        self, dataset_item_id: int, file_path: Path, byte_read_callback: Optional[ByteReadCallback]
    ) -> None:
        pass


class UploadHandlerV1(UploadHandler):
    def __init__(self, dataset: "RemoteDataset", local_files: List[LocalFile]):
        super().__init__(dataset=dataset, local_files=local_files)

    def _request_upload(self) -> Tuple[List[ItemPayload], List[ItemPayload]]:
        blocked_items = []
        items = []
        chunk_size: int = _upload_chunk_size()
        for file_chunk in chunk(self.local_files, chunk_size):
            upload_payload = {"items": [file.data for file in file_chunk]}
            dataset_slug: str = self.dataset_identifier.dataset_slug
            team_slug: Optional[str] = self.dataset_identifier.team_slug

            data: Dict[str, Any] = self.client.upload_data(dataset_slug, upload_payload, team_slug)

            blocked_items.extend([ItemPayload(**item) for item in data["blocked_items"]])
            items.extend([ItemPayload(**item) for item in data["items"]])
        return blocked_items, items

    def _upload_files(self) -> Iterator[Callable[[Optional[ByteReadCallback]], None]]:
        def upload_function(dataset_item_id, local_path) -> Callable[[Optional[ByteReadCallback]], None]:
            return lambda byte_read_callback=None: self._upload_file(dataset_item_id, local_path, byte_read_callback)

        file_lookup = {file.full_path: file for file in self.local_files}
        for item in self.pending_items:
            file = file_lookup.get(item.full_path)
            if not file:
                raise ValueError(f"Cannot match {item.full_path} from payload with files to upload")
            yield upload_function(item.dataset_item_id, file.local_path)

    def _upload_file(
        self, dataset_item_id: int, file_path: Path, byte_read_callback: Optional[ByteReadCallback]
    ) -> None:
        try:
            self._do_upload_file(dataset_item_id, file_path, byte_read_callback)
        except UploadRequestError as e:
            self.errors.append(e)
        except Exception as e:
            self.errors.append(UploadRequestError(file_path=file_path, stage=UploadStage.OTHER, error=e))

    def _do_upload_file(
        self,
        dataset_item_id: int,
        file_path: Path,
        byte_read_callback: Optional[ByteReadCallback] = None,
    ) -> None:
        team_slug: Optional[str] = self.dataset_identifier.team_slug

        try:
            sign_response: Dict[str, Any] = self.client.sign_upload(dataset_item_id, team_slug)
        except Exception as e:
            raise UploadRequestError(file_path=file_path, stage=UploadStage.REQUEST_SIGNATURE, error=e)

        upload_url = sign_response["upload_url"]

        try:
            file_size = file_path.stat().st_size
            if byte_read_callback:
                byte_read_callback(str(file_path), file_size, 0)

            def callback(monitor):
                if byte_read_callback:
                    byte_read_callback(str(file_path), file_size, monitor.bytes_read)

            with file_path.open("rb") as m:
                monitor = FileMonitor(m, file_size, callback)

                retries = 0
                while retries < 5:
                    upload_response = requests.put(f"{upload_url}", data=monitor)
                    # If s3 is getting to many request it will return 503, we will sleep and retry
                    if upload_response.status_code != 503:
                        break

                    time.sleep(2**retries)
                    retries += 1

            upload_response.raise_for_status()
        except Exception as e:
            raise UploadRequestError(file_path=file_path, stage=UploadStage.UPLOAD_TO_S3, error=e)

        try:
            self.client.confirm_upload(dataset_item_id, team_slug)
        except Exception as e:
            raise UploadRequestError(file_path=file_path, stage=UploadStage.CONFIRM_UPLOAD_COMPLETE, error=e)


class UploadHandlerV2(UploadHandler):
    def __init__(self, dataset: "RemoteDataset", local_files: List[LocalFile]):
        super().__init__(dataset=dataset, local_files=local_files)

    def _request_upload(self) -> Tuple[List[ItemPayload], List[ItemPayload]]:
        blocked_items = []
        items = []
        chunk_size: int = _upload_chunk_size()
        for file_chunk in chunk(self.local_files, chunk_size):
            upload_payload = {"items": [file.serialize_v2() for file in file_chunk]}
            dataset_slug: str = self.dataset_identifier.dataset_slug
            team_slug: Optional[str] = self.dataset_identifier.team_slug

            data: Dict[str, Any] = self.client.api_v2.register_data(dataset_slug, upload_payload, team_slug=team_slug)

            blocked_items.extend([ItemPayload.parse_v2(item) for item in data["blocked_items"]])
            items.extend([ItemPayload.parse_v2(item) for item in data["items"]])
        return blocked_items, items

    def _upload_files(self) -> Iterator[Callable[[Optional[ByteReadCallback]], None]]:
        def upload_function(dataset_slug, local_path, upload_id) -> Callable[[Optional[ByteReadCallback]], None]:
            return lambda byte_read_callback=None: self._upload_file(
                dataset_slug, local_path, upload_id, byte_read_callback
            )

        file_lookup = {file.full_path: file for file in self.local_files}
        for item in self.pending_items:
            if len(item.slots) != 1:
                raise NotImplemented("Multi file upload is not supported")
            upload_id = item.slots[0]["upload_id"]
            file = file_lookup.get(item.full_path)
            if not file:
                raise ValueError(f"Cannot match {item.full_path} from payload with files to upload")
            yield upload_function(self.dataset.identifier.dataset_slug, file.local_path, upload_id)

    def _upload_file(
        self, dataset_slug: str, file_path: Path, upload_id: str, byte_read_callback: Optional[ByteReadCallback]
    ) -> None:
        try:
            self._do_upload_file(dataset_slug, file_path, upload_id, byte_read_callback)
        except UploadRequestError as e:
            self.errors.append(e)
        except Exception as e:
            self.errors.append(UploadRequestError(file_path=file_path, stage=UploadStage.OTHER, error=e))

    def _do_upload_file(
        self,
        dataset_slug: str,
        file_path: Path,
        upload_id: str,
        byte_read_callback: Optional[ByteReadCallback] = None,
    ) -> None:
        team_slug: Optional[str] = self.dataset_identifier.team_slug

        try:
            sign_response: Dict[str, Any] = self.client.api_v2.sign_upload(dataset_slug, upload_id, team_slug=team_slug)
        except Exception as e:
            raise UploadRequestError(file_path=file_path, stage=UploadStage.REQUEST_SIGNATURE, error=e)

        upload_url = sign_response["upload_url"]

        try:
            file_size = file_path.stat().st_size
            if byte_read_callback:
                byte_read_callback(str(file_path), file_size, 0)

            def callback(monitor):
                if byte_read_callback:
                    byte_read_callback(str(file_path), file_size, monitor.bytes_read)

            with file_path.open("rb") as m:
                monitor = FileMonitor(m, file_size, callback)

                retries = 0
                while retries < 5:
                    upload_response = requests.put(f"{upload_url}", data=monitor)
                    # If s3 is getting to many request it will return 503, we will sleep and retry
                    if upload_response.status_code != 503:
                        break

                    time.sleep(2**retries)
                    retries += 1

            upload_response.raise_for_status()
        except Exception as e:
            raise UploadRequestError(file_path=file_path, stage=UploadStage.UPLOAD_TO_S3, error=e)

        try:
            self.client.api_v2.confirm_upload(dataset_slug, upload_id, team_slug=team_slug)
        except Exception as e:
            raise UploadRequestError(file_path=file_path, stage=UploadStage.CONFIRM_UPLOAD_COMPLETE, error=e)


DEFAULT_UPLOAD_CHUNK_SIZE: int = 500


def _upload_chunk_size() -> int:
    """
    Gets the chunk size to be used from the OS environment, or uses the default one if that is not
    possible. The default chunk size is 500.

    Returns
    -------
    int
        The chunk size to be used.
    """
    env_chunk: Optional[str] = os.getenv("DARWIN_UPLOAD_CHUNK_SIZE")
    if env_chunk is None:
        return DEFAULT_UPLOAD_CHUNK_SIZE

    try:
        return int(env_chunk)
    except ValueError:
        print("Cannot cast environment variable DEFAULT_UPLOAD_CHUNK_SIZE to integer")
        print(f"Setting chunk size to {DEFAULT_UPLOAD_CHUNK_SIZE}")
        return DEFAULT_UPLOAD_CHUNK_SIZE
