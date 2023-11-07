from unittest.mock import Mock
from uuid import UUID

import pytest
import responses

from darwin.exceptions import DarwinException
from darwin.future.core.client import ClientCore
from darwin.future.core.items.delete_items import delete_list_of_items
from darwin.future.tests.core.fixtures import *


@responses.activate
def test_delete_items_including_filters(base_client: ClientCore) -> None:
    # Define the expected response
    responses.add(
        responses.DELETE,
        base_client.config.api_endpoint + "v2/teams/test-team/items",
        json={"affected_item_count": 2},
    )

    # Call the function
    response = delete_list_of_items(
        api_client=base_client,
        team_slug="test-team",
        dataset_id=000000,
        item_ids=[
            UUID("00000000-0000-0000-0000-000000000000"),
            UUID("00000000-0000-0000-0000-000000000000"),
        ],
        filters={
            "not_statuses": ["uploading", "annotate"],
            "not_assignees": [123, 456, 789],
        },
    )

    # Check that the response mathces what we expect
    assert response == {"affected_item_count": 2}


def test_delete_items_with_error_response() -> None:
    api_client = Mock(spec=ClientCore)
    api_client.delete.side_effect = DarwinException("Something went wrong")

    with pytest.raises(DarwinException):
        delete_list_of_items(
            api_client=api_client,
            team_slug="test-team",
            dataset_id=000000,
            item_ids=[
                UUID("00000000-0000-0000-0000-000000000000"),
                UUID("00000000-0000-0000-0000-000000000000"),
            ],
        )
