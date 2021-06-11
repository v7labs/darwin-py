from dataclasses import dataclass
from typing import Optional


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
        return "/".join(filter(None, [self.path, self.filename]))


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
