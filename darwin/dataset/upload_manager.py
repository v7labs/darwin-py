import concurrent.futures
import os
import time
from dataclasses import dataclass
from enum import Enum
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
from darwin.path_utils import construct_full_path
from darwin.utils import chunk

if TYPE_CHECKING:
    from darwin.client import Client
    from darwin.dataset import RemoteDataset
    from darwin.dataset.identifier import DatasetIdentifier

from typing import Dict


class ItemPayload:
    def __init__(self, *, dataset_item_id: int, filename: str, path: str, reason: Optional[str] = None):
        self.dataset_item_id = dataset_item_id
        self.filename = filename
        self.path = path
        self.reason = reason

    @property
    def full_path(self) -> str:
        return construct_full_path(self.path, self.filename)


class UploadStage(Enum):
    REQUEST_SIGNATURE = 0
    UPLOAD_TO_S3 = 1
    CONFIRM_UPLOAD_COMPLETE = 2
    OTHER = 3


@dataclass
class UploadRequestError(Exception):
    file_path: Path
    stage: UploadStage
    error: Optional[Exception] = None


class LocalFile:
    def __init__(self, local_path: PathLike, **kwargs):
        self.local_path = Path(local_path)
        self.data = kwargs
        self._type_check(kwargs)

    def _type_check(self, args) -> None:
        self.data["filename"] = args.get("filename") or self.local_path.name
        self.data["path"] = args.get("path") or "/"

    @property
    def full_path(self) -> str:
        return construct_full_path(self.data["path"], self.data["filename"])


class FileMonitor(object):
    """
    An object used to monitor the progress of a :class:`BufferedReader`.

    To use this monitor, you construct your :class:`BufferedReader` as you
    normally would, then construct this object with it as argument.

    Attributes
    ----------
    bytes_read: int
      Amount of bytes read from the IO.
    len: int
        Total size of the IO.
    io: BinaryIO
        IO object used by this class. Depency injection.
    callback: Callable[["FileMonitor"], None]
        Callable function used by this class. Depency injection.
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
        size: int
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


class UploadHandler:
    def __init__(self, dataset: "RemoteDataset", local_files: List[LocalFile]):
        self.dataset: RemoteDataset = dataset
        self.errors: List[UploadRequestError] = []
        self.local_files: List[LocalFile] = local_files
        self._progress: Optional[Iterator[Callable[[Optional[ByteReadCallback]], None]]] = None

        self.blocked_items, self.pending_items = self._request_upload()

    @property
    def client(self) -> "Client":
        return self.dataset.client

    @property
    def dataset_identifier(self) -> "DatasetIdentifier":
        return self.dataset.identifier

    @property
    def blocked_count(self) -> int:
        return len(self.blocked_items)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def pending_count(self) -> int:
        return len(self.pending_items)

    @property
    def total_count(self) -> int:
        return self.pending_count + self.blocked_count

    @property
    def progress(self):
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
        self, dataset_item_id: int, file_path: Path, byte_read_callback: Optional[ByteReadCallback] = None,
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

                    time.sleep(2 ** retries)
                    retries += 1

            upload_response.raise_for_status()
        except Exception as e:
            raise UploadRequestError(file_path=file_path, stage=UploadStage.UPLOAD_TO_S3, error=e)

        try:
            self.client.confirm_upload(dataset_item_id, team_slug)
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
