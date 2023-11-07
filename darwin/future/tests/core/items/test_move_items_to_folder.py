from unittest.mock import Mock
from uuid import UUID

import pytest
import responses

from darwin.exceptions import DarwinException
from darwin.future.core.client import ClientCore
from darwin.future.core.items.move_items_to_folder import move_list_of_items_to_folder
from darwin.future.tests.core.fixtures import *


@responses.activate
def test_move_list_of_items_to_folder_including_filters(
    base_client: ClientCore,
) -> None:
    # Define the expected response
    responses.add(
        responses.POST,
        base_client.config.api_endpoint + "v2/teams/test-team/items/path",
        json={"affected_item_count": 2},
    )

    # Call the function
    response = move_list_of_items_to_folder(
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
        path="/test/path",
    )

    # Check that the response mathces what we expect
    assert response == {"affected_item_count": 2}


def test_move_list_of_items_to_folder_with_error_response() -> None:
    api_client = Mock(spec=ClientCore)
    api_client.post.side_effect = DarwinException("Something went wrong")

    with pytest.raises(DarwinException):
        move_list_of_items_to_folder(
            api_client=api_client,
            team_slug="test-team",
            dataset_id=000000,
            item_ids=[
                UUID("00000000-0000-0000-0000-000000000000"),
                UUID("00000000-0000-0000-0000-000000000000"),
            ],
            path="/test/path",
        )
