import concurrent.futures
import multiprocessing
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Callable, List, Optional, Set, Tuple, Union

import requests
from darwin.path_utils import construct_full_path
from darwin.utils import chunk
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

if TYPE_CHECKING:
    from darwin.client import Client
    from darwin.dataset import RemoteDataset
    from darwin.dataset.identifier import DatasetIdentifier


class ItemPayload:
    def __init__(self, *, dataset_item_id: int, filename: str, path: str, reason: Optional[str] = None):
        self.dataset_item_id = dataset_item_id
        self.filename = filename
        self.path = path
        self.reason = reason

    @property
    def full_path(self):
        return construct_full_path(self.path, self.filename)


class LocalFile:
    def __init__(self, local_path: Union[str, Path], **kwargs):
        self.local_path = Path(local_path)
        self.data = kwargs
        self._type_check(kwargs)

    def _type_check(self, args):
        self.data["filename"] = args.get("filename") or self.local_path.name
        self.data["path"] = args.get("path") or "/"

    @property
    def full_path(self):
        return construct_full_path(self.data["path"], self.data["filename"])


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


ByteReadCallback = Callable[[Optional[str], float, float], None]
ProgressCallback = Callable[[int, float], None]
FileUploadCallback = Callable[[str, int, int], None]


class UploadHandler:
    def __init__(self, dataset: "RemoteDataset", local_files: List[LocalFile]):
        self.dataset = dataset
        self.errors: List[UploadRequestError] = []
        self.local_files = local_files
        self._progress = None

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

    def prepare_upload(self):
        self._progress = self._upload_files()
        return self._progress

    def upload(
        self,
        multi_threaded: bool = True,
        progress_callback: Optional[ProgressCallback] = None,
        file_upload_callback: Optional[FileUploadCallback] = None,
        max_workers: Optional[int] = None,
    ):
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

        if multi_threaded:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_progress = {executor.submit(f, callback) for f in self.progress}
                for future in concurrent.futures.as_completed(future_to_progress):
                    try:
                        future.result()
                    except Exception as exc:
                        print("exception", exc)
        else:
            for file_to_upload in self.progress:
                file_to_upload(callback)

    def _request_upload(self) -> Tuple[List[ItemPayload], List[ItemPayload]]:
        blocked_items = []
        items = []
        for file_chunk in chunk(self.local_files, 500):
            upload_payload = {"items": [file.data for file in file_chunk]}
            data = self.client.put(
                endpoint=f"/teams/{self.dataset_identifier.team_slug}/datasets/{self.dataset_identifier.dataset_slug}/data",
                payload=upload_payload,
                team=self.dataset_identifier.team_slug,
            )
            blocked_items.extend([ItemPayload(**item) for item in data["blocked_items"]])
            items.extend([ItemPayload(**item) for item in data["items"]])
        return blocked_items, items

    def _upload_files(self):
        def upload_function(dataset_item_id, local_path):
            return lambda byte_read_callback=None: self._upload_file(dataset_item_id, local_path, byte_read_callback)

        file_lookup = {file.full_path: file for file in self.local_files}
        for item in self.pending_items:
            file = file_lookup.get(item.full_path)
            if not file:
                raise ValueError(f"Cannot match {item.full_path} from payload with files to upload")
            yield upload_function(item.dataset_item_id, file.local_path)

    def _upload_file(self, dataset_item_id: int, file_path: Path, byte_read_callback):
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
    ):
        team_slug = self.dataset_identifier.team_slug

        try:
            sign_response = self.client.get(f"/dataset_items/{dataset_item_id}/sign_upload", team=team_slug, raw=True)
            sign_response.raise_for_status()
            sign_response = sign_response.json()
        except Exception as e:
            raise UploadRequestError(file_path=file_path, stage=UploadStage.REQUEST_SIGNATURE, error=e)

        signature = sign_response["signature"]
        end_point = sign_response["postEndpoint"]

        try:
            file_size = file_path.stat().st_size
            if byte_read_callback:
                byte_read_callback(str(file_path), file_size, 0)

            def callback(monitor):
                # The signature is part of the payload's bytes_read but not file_size
                # therefore we should skip it in the upload progress
                bytes_read = max(monitor.bytes_read - monitor.len + file_size, 0)
                if byte_read_callback:
                    byte_read_callback(str(file_path), file_size, bytes_read)

            m = MultipartEncoder(fields={**signature, **{"file": file_path.open("rb")}})
            monitor = MultipartEncoderMonitor(m, callback)
            headers = {"Content-Type": monitor.content_type}

            retries = 0
            while retries < 5:
                upload_response = requests.post(f"http:{end_point}", data=monitor, headers=headers)
                # If s3 is getting to many request it will return 503, we will sleep and retry
                if upload_response.status_code != 503:
                    break

                time.sleep(2 ** retries)
                retries += 1

            upload_response.raise_for_status()
        except Exception as e:
            raise UploadRequestError(file_path=file_path, stage=UploadStage.UPLOAD_TO_S3, error=e)

        try:
            confirm_response = self.client.put(
                endpoint=f"/dataset_items/{dataset_item_id}/confirm_upload", payload={}, team=team_slug, raw=True
            )
            confirm_response.raise_for_status()
        except Exception as e:
            raise UploadRequestError(file_path=file_path, stage=UploadStage.CONFIRM_UPLOAD_COMPLETE, error=e)
