from __future__ import annotations

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONType
from darwin.future.data_objects.typing import UnknownType


def tag_items(
    client: ClientCore,
    team_slug: str,
    dataset_ids: int | list[int],
    tag_id: int,
    filters: dict[str, UnknownType],
) -> JSONType:
    """
    Adds tag annotation to all items slots matched by filters.

    Args:
        client (ClientCore): The Darwin Core client.
        team_slug (str): The team slug.
        dataset_ids (int | list[int]): The dataset ids.
        tag_id (int): The tag id.
        filters Dict[str, UnknownType]: The parameters of the filter.

    Returns:
        JSONType: The response data.
    """
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
        "annotation_class_id": tag_id,
    }

    return client.post(f"/v2/teams/{team_slug}/items/slots/tags", data=payload)
