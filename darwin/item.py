from dataclasses import dataclass


@dataclass(frozen=True, eq=True)
class DatasetItem:
    id: int
    filename: str
    status: str
    archived: bool
    filesize: int
    dataset_id: int
    dataset_slug: str


def parse_dataset_item(raw) -> DatasetItem:
    return DatasetItem(
        raw["id"], raw["filename"], raw["status"], raw["archived"], raw["file_size"], raw["dataset_id"], "n/a"
    )
