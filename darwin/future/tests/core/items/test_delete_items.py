from uuid import UUID

import responses

from darwin.future.core.client import ClientCore
from darwin.future.core.items.delete_items import delete_list_of_items
from darwin.future.tests.core.fixtures import *


@responses.activate
def test_delete_items_including_filters(base_client: ClientCore) -> None:

    responses.add(
        responses.DELETE,
        base_client.config.api_endpoint + "v2/teams/test-team/items",
        json={"affected_item_count": 2},
        status=200,
    )

    response = delete_list_of_items(
        client=base_client,
        team_slug="test-team",
        dataset_ids=000000,
        item_ids=[
            UUID("00000000-0000-0000-0000-000000000000"),
            UUID("00000000-0000-0000-0000-000000000000"),
        ],
        filters={
            "not_statuses": ["uploading", "annotate"],
            "not_assignees": [123, 456, 789],
        },
    )

    assert response == {"affected_item_count": 2}
