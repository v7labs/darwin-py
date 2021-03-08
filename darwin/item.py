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


def parse_dataset_item(raw) -> DatasetItem:
    return DatasetItem(
        raw["id"],
        parse_filename(raw),
        raw["status"],
        raw["archived"],
        raw["file_size"],
        raw["dataset_id"],
        "n/a",
        raw["seq"],
        raw.get("current_workflow_id"),
    )

def parse_filename(raw):
    if raw["dataset_image"] is not None:
        return raw["dataset_image"]["image"]["original_filename"]
    if raw["dataset_video"] is not None:
        return raw["dataset_video"]["original_filename"]
    return raw["filename"]
