import concurrent.futures
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Tuple

import requests
from darwin.path_utils import construct_full_path

if TYPE_CHECKING:
    from darwin.client import Client
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
    def __init__(self, local_path: str, **kwargs):
        self.local_path = Path(local_path)
        self.data = kwargs
        self._type_check(kwargs)

    def _type_check(self, args):
        self.data["filename"] = args.get("filename") or self.local_path.name
        self.data["remote_path"] = args.get("path") or "/"

    @property
    def full_path(self):
        return construct_full_path(self.data["remote_path"], self.data["filename"])


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


class UploadHandler:
    def __init__(self, client: "Client", local_files: List[LocalFile], dataset_identifier: "DatasetIdentifier"):
        self.client = client
        self.dataset_identifier = dataset_identifier
        self.errors: List[UploadRequestError] = []
        self.local_files = local_files
        self._progress = None

        self.blocked_items, self.pending_items = self._request_upload()

    @property
    def blocked_count(self):
        return len(self.blocked_items)

    @property
    def error_count(self):
        return len(self.errors)

    @property
    def pending_count(self):
        return len(self.pending_items)

    @property
    def total_count(self):
        return self.pending_count + self.blocked_count

    @property
    def progress(self):
        return self._progress

    def prepare_upload(self):
        self._progress = self._upload_files()
        return self._progress

    def upload(self, multi_threaded: bool = True, progress_callback: Optional[Callable[[int, int], None]] = None):
        if not self._progress:
            self.prepare_upload()
        if progress_callback:
            progress_callback(self.pending_count, 0)
        
        if multi_threaded:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future_to_progress = {executor.submit(f): f for f in self.progress}
                for future in concurrent.futures.as_completed(future_to_progress):
                    try:
                        future.result()
                    except Exception as exc:
                        print(exc)
                    else:
                        if progress_callback:
                            progress_callback(self.pending_count, 1)
        else:
            for file_to_upload in self.progress:
                file_to_upload()
                if progress_callback:
                    progress_callback(self.pending_count, 1)

    def _request_upload(self) -> Tuple[List[ItemPayload], List[ItemPayload]]:
        upload_payload = {"items": [file.data for file in self.local_files]}
        data = self.client.put(
            endpoint=f"/teams/{self.dataset_identifier.team_slug}/datasets/{self.dataset_identifier.dataset_slug}/data",
            payload=upload_payload,
            team=self.dataset_identifier.team_slug,
        )
        blocked_items = [ItemPayload(**item) for item in data["blocked_items"]]
        items = [ItemPayload(**item) for item in data["items"]]
        return blocked_items, items

    def _upload_files(self):
        file_lookup = {file.full_path: file for file in self.local_files}
        for item in self.pending_items:
            file = file_lookup.get(item.full_path)
            if not file:
                raise ValueError(f"Cannot match {item.full_path} from payload with files to upload")
            yield lambda: self._upload_file(item.dataset_item_id, file.local_path)

    def _upload_file(self, dataset_item_id: int, file_path: Path):
        try:
            self._do_upload_file(dataset_item_id, file_path)
        except UploadRequestError as e:
            self.errors.append(e)
        except Exception as e:
            self.errors.append(UploadRequestError(file_path=file_path, stage=UploadStage.OTHER, error=e))
        

    def _do_upload_file(self, dataset_item_id: int, file_path: Path):
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
            upload_response = requests.post(f"http:{end_point}", data=signature, files={"file": file_path.open("rb")})
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
