from __future__ import annotations

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONType
from darwin.future.data_objects.item import ItemLayout


def set_item_layout(
    client: ClientCore,
    team_slug: str,
    dataset_ids: int | list[int],
    layout: ItemLayout,
    params: JSONType,
) -> JSONType:
    """
    Set the layout of a dataset and filtered items via params.

    Args:
        client (ClientCore): The Darwin Core client.
        team_slug (str): The team slug.
        dataset_ids (int | list[int]): The dataset ids.
        layout (ItemLayout): The layout.
        params (JSONType): The parameters.

    Returns:
        JSONType: The response data.
    """
    assert (
        params
    ), "No parameters provided, please provide at least one non-dataset id filter"
    assert isinstance(params, dict), "Parameters must be a dictionary of filters"
    payload = {
        "filters": {
            "dataset_ids": dataset_ids
            if isinstance(dataset_ids, list)
            else [dataset_ids],
            **params,
        },
        "layout": dict(layout),
    }

    return client.post(f"/v2/teams/{team_slug}/items/layout", data=payload)
