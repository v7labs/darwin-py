from dataclasses import dataclass
from typing import Any, Dict, Optional

from darwin.path_utils import construct_full_path


@dataclass(frozen=True, eq=True)
class DatasetItem:
    """
    DatasetItem represents files that can be images or videos which belong to a dataset.

    Attributes
    ----------
    id : int
        The id of this ``DatasetItem``.
    filename : str
        The filename of this ``DatasetItem``.
    status : str
        The status of this ``DatasetItem``. It can be: 
        - "archived",
        - "error",
        - "uploading",
        - "processing",
        - "new",
        - "annotate",
        - "review",
        - "complete"
    archived : bool
        Whether or not this item was soft deleted.
    filesize : int
        The size of this ``DatasetItem``'s file in bytes.
    dataset_id : int
        The id of the ``Dataset`` this ``DatasetItem`` belongs to.
    dataset_slug : str
        The slugified name of the ``Dataset`` this ``DatasetItem`` belongs to.
    seq : int
        The sequential value of this ``DatasetItem`` in relation to the ``Dataset`` it belongs to.
        This allows us to know which items were added first and is used mostly for sorting purposes.
    current_workflow_id : Optional[int], default : None
        The id of this ``DatasetItem``'s workflow. A ``None`` value means this ``DatasetItem`` is 
        new and was never worked on, or was reseted to the new state.
    path : str
        The darwin path to this ``DatasetItem``.
    """

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
        """
        The full POSIX relative path of this ``DatasetItem``.
        """
        return construct_full_path(self.path, self.filename)


def parse_dataset_item(raw: Dict[str, Any]) -> DatasetItem:
    """
    Parses the given dictionary into a ``DatasetItem``. Raises if such is not possible.

    Parameters
    ----------
    raw : Dict[str, Any]
        The dictionary to parse.

    Returns
    -------
    DatasetItem
        A dataset item with the parsed information.
    """
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
