from unittest.mock import Mock
from uuid import UUID

import pytest
import responses

from darwin.exceptions import DarwinException
from darwin.future.core.client import ClientCore
from darwin.future.core.items.archive_items import archive_list_of_items
from darwin.future.tests.core.fixtures import *


@responses.activate
def test_archive_items_including_filters(base_client: ClientCore) -> None:
    # Define the expected response
    responses.add(
        responses.POST,
        base_client.config.api_endpoint + "v2/teams/test-team/items/archive",
        json={"affected_item_count": 2},
    )

    # Call the function
    response = archive_list_of_items(
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


def test_archive_items_with_error_response() -> None:
    api_client = Mock(spec=ClientCore)
    api_client.post.side_effect = DarwinException("Something went wrong")

    with pytest.raises(DarwinException):
        archive_list_of_items(
            api_client=api_client,
            team_slug="test-team",
            dataset_id=000000,
            item_ids=[
                UUID("00000000-0000-0000-0000-000000000000"),
                UUID("00000000-0000-0000-0000-000000000000"),
            ],
        )
