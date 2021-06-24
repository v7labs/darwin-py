from dataclasses import dataclass
from typing import Optional

from darwin.utils import urljoin


@dataclass(frozen=True, eq=True)
class DatasetItem:
    id: int
    filename: str
    status: str
    archived: bool
    filesize: int
    dataset_id: int
    dataset_slug: str
    seq: int
    current_workflow_id: Optional[int]
    path: str

    @property
    def full_path(self) -> str:
        return urljoin(*filter(None, [self.remote_path, self.filename]))

    @property
    def remote_path(self) -> str:
        if not self.path.startswith("/"):
            return self.path

        parts = self.path.split("/")[1:]
        return urljoin(*parts)


def parse_dataset_item(raw) -> DatasetItem:
    return DatasetItem(
        raw["id"],
        raw["filename"],
        raw["status"],
        raw["archived"],
        raw["file_size"],
        raw["dataset_id"],
        "n/a",
        raw["seq"],
        raw.get("current_workflow_id"),
        raw["path"],
    )
