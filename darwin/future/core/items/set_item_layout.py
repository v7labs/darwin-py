from __future__ import annotations

from typing import Dict

from pydantic import ValidationError

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONType
from darwin.future.data_objects.item import ItemLayout
from darwin.future.data_objects.typing import UnknownType
from darwin.future.exceptions import BadRequest


def set_item_layout(
    client: ClientCore,
    team_slug: str,
    dataset_ids: int | list[int],
    layout: ItemLayout,
    filters: Dict[str, UnknownType],
) -> JSONType:
    """
    Set the layout of a dataset and filtered items via filters.

    Args:
        client (ClientCore): The Darwin Core client.
        team_slug (str): The team slug.
        dataset_ids (int | list[int]): The dataset ids.
        layout (ItemLayout): The layout.
        filters Dict[str, UnknownType]: The parameters of the filter.

    Returns:
        JSONType: The response data.
    """
    if not isinstance(layout, ItemLayout):
        try:
            layout = ItemLayout.model_validate(layout)
        except (ValueError, ValidationError):
            raise BadRequest("Invalid layout provided")

    assert (
        filters
    ), "No parameters provided, please provide at least one non-dataset id filter"
    payload = {
        "filters": {
            "dataset_ids": (
                dataset_ids if isinstance(dataset_ids, list) else [dataset_ids]
            ),
            **filters,
        },
        "layout": dict(layout),
    }

    return client.post(f"/v2/teams/{team_slug}/items/layout", data=payload)
