import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import darwin.datatypes as dt
from darwin.utils import parse_darwin_json


@dataclass
class StageVisit:
    """
    One workflow stage visit of an item, as listed in ``stage_history/<item id>/visits.json``
    of an export created with ``include_stage_history``.

    Attributes
    ----------
    stage_instance_id : str
        ID of the visit.
    parent_stage_id : Optional[str]
        ID of the parallel stage the visit belongs to, if any.
    stage : Dict[str, str]
        ``id``, ``name`` and ``type`` of the visited stage.
    status : Literal["completed", "overriden", "current"]
        How the visit ended, or ``current`` if the item is still in it.
    entered_at : str
        When the visit started (ISO 8601).
    exited_at : Optional[str]
        When the visit ended (ISO 8601), ``None`` if it hasn't.
    exited_by : Optional[Dict[str, Any]]
        Who ended the visit: ``type`` (``user``, ``model`` or ``system``) and ``id``, plus
        ``email`` and ``full_name`` for users when exported with ``include_authorship``.
        ``None`` if the visit hasn't ended or ended before this was recorded.
    exit_snapshot : Dict[str, Optional[str]]
        ``status`` (``exported`` or ``none``) and the snapshot ``file`` name.
    snapshot_path : Optional[Path]
        Path to the snapshot file, ``None`` if the visit has no exported snapshot.
    """

    stage_instance_id: str
    parent_stage_id: Optional[str]
    stage: Dict[str, str]
    status: Literal["completed", "overriden", "current"]
    entered_at: str
    exited_at: Optional[str]
    exited_by: Optional[Dict[str, Any]]
    exit_snapshot: Dict[str, Optional[str]]
    snapshot_path: Optional[Path]

    def snapshot(self) -> Optional[dt.AnnotationFile]:
        """
        Parses the annotations, annotation properties and item properties the item had at
        the end of this visit.

        Returns
        -------
        Optional[dt.AnnotationFile]
            The parsed Darwin JSON snapshot, or ``None`` if the visit has no exported snapshot.
        """
        return parse_darwin_json(self.snapshot_path) if self.snapshot_path else None


def read_stage_history(item_dir: Path) -> List[StageVisit]:
    """
    Reads the stage history of one item from a pulled export.

    Parameters
    ----------
    item_dir : Path
        The ``stage_history/<item id>`` directory, which holds ``visits.json`` and the snapshots.

    Returns
    -------
    List[StageVisit]
        The item's visits, in the order they happened.
    """
    item_dir = Path(item_dir)
    with (item_dir / "visits.json").open(encoding="utf-8") as f:
        data = json.load(f)
    return [
        StageVisit(
            stage_instance_id=visit["stage_instance_id"],
            parent_stage_id=visit.get("parent_stage_id"),
            stage=visit["stage"],
            status=visit["status"],
            entered_at=visit["entered_at"],
            exited_at=visit.get("exited_at"),
            exited_by=visit.get("exited_by"),
            exit_snapshot=visit["exit_snapshot"],
            snapshot_path=(
                item_dir / visit["exit_snapshot"]["file"]
                if visit["exit_snapshot"]["status"] == "exported"
                else None
            ),
        )
        for visit in data["visits"]
    ]
