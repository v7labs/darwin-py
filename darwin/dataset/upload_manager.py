from pathlib import Path
from typing import TYPE_CHECKING, List

import requests

if TYPE_CHECKING:
    from darwin.client import Client

from rich.console import Console
from rich.table import Table


class LocalFile:
    def __init__(self, local_path, **kwargs):
        self.local_path = Path(local_path)
        self.data = kwargs
        self._type_check(kwargs)

    def _type_check(self, args):
        self.data["filename"] = args.get("filename") or self.local_path.name


class UploadHandler:
    def __init__(self, client, local_files, dataset_identifier):
        self.client = client
        self.local_files = local_files
        self.dataset_identifier = dataset_identifier

        self.blocked_items, self.pending_items = request_upload(client, local_files, dataset_identifier)

    @property
    def pending_count(self):
        return len(self.pending_items)

    @property
    def blocked_count(self):
        return len(self.blocked_items)

    @property
    def total_count(self):
        return self.pending_count + self.blocked_count

    @property
    def progress(self):
        return self._progress

    def show_breakdown(self, verbose: bool) -> None:
        console = Console()

        if not self.blocked_count:
            console.print(f"All {self.total_count} files will be uploaded.")
            return

        console.print(f"{self.blocked_count} out of {self.total_count} files will not be uploaded.")

        if not verbose:
            console.print('Re-run with "--verbose" for further details')
            return

        blocked_items_table = Table(show_header=True, header_style="bold blue")
        blocked_items_table.add_column("Dataset Item ID")
        blocked_items_table.add_column("Filename")
        blocked_items_table.add_column("Reason")
        for item in self.blocked_items:
            blocked_items_table.add_row(*map(str, item.values()))

        console.print(blocked_items_table)

    def upload(self):
        self._progress = _upload_files(
            self.client, self.local_files, self.pending_items, self.dataset_identifier.team_slug
        )
        return self._progress


def request_upload(client: "Client", files: List[LocalFile], dataset_identifier):
    upload_payload = {"items": [file.data for file in files]}
    data = client.put(
        endpoint=f"/teams/{dataset_identifier.team_slug}/datasets/{dataset_identifier.dataset_slug}/data",
        payload=upload_payload,
        team=dataset_identifier.team_slug,
    )
    return data["blocked_items"], data["items"]


def _upload_files(client: "Client", files: List[LocalFile], items_pending_upload, team_slug: str):
    file_lookup = {file.data["filename"]: file for file in files}
    for item in items_pending_upload:
        file = file_lookup.get(item["filename"])
        if not file:
            raise ValueError(f"Can not match {item['filename']} from payload with files to upload")
        yield lambda: _upload_file(client, item["dataset_item_id"], file.local_path, team_slug=team_slug)


def _upload_file(client: "Client", dataset_item_id: int, file_path: Path, team_slug: str):
    print("about to request signature")
    sign_response = client.get(f"/dataset_items/{dataset_item_id}/sign_upload", team=team_slug)
    signature = sign_response["signature"]
    end_point = sign_response["postEndpoint"]

    print("about to post to s3")
    upload_response = requests.post("http:" + end_point, data=signature, files={"file": file_path.open("rb")})
    upload_response.raise_for_status()

    print("about to confirm upload complete")
    client.put(endpoint=f"/dataset_items/{dataset_item_id}/confirm_upload", payload={}, team=team_slug)
