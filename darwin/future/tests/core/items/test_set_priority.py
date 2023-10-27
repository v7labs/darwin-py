from unittest.mock import Mock
from uuid import UUID

import pytest
import responses

from darwin.exceptions import DarwinException
from darwin.future.core.client import ClientCore
from darwin.future.core.items.set_item_priority import set_item_priority
from darwin.future.tests.core.fixtures import *


@responses.activate
def test_set_item_priority(base_client) -> None:
    responses.add(
        responses.POST,
        base_client.config.api_endpoint + "v2/teams/test-team/items/priority",
        json={"affected_item_count": 1},
    )

    response = set_item_priority(
        base_client,
        "test-team",
        123,
        [UUID("00000000-0000-0000-0000-000000000000")],
        999,
    )

    assert response == {"affected_item_count": 1}


def test_set_item_priority_with_filters() -> None:
    base_client = Mock(spec=ClientCore)

    expected_payload = {
        "priority": 10,
        "filters": {
            "dataset_ids": [123],
            "item_ids": ["00000000-0000-0000-0000-000000000000"],
            "status": "open",
        },
    }

    # Define the expected endpoint
    expected_endpoint = "/v2/teams/test-team/items/priority"

    # Define the expected response
    expected_response = {"status": "success"}

    # Configure the mock API client to return the expected response
    base_client.post.return_value = expected_response

    # Call the function being tested
    response = set_item_priority(
        base_client,
        "test-team",
        123,
        [UUID("00000000-0000-0000-0000-000000000000")],
        priority=10,
        filters={"status": "open"},
    )

    # Verify that the API client was called with the expected arguments
    base_client.post.assert_called_once_with(
        endpoint=expected_endpoint,
        data=expected_payload,
    )

    # Verify that the response matches the expected response
    assert response == expected_response


def test_set_item_priority_with_error_response() -> None:
    # Create a mock API client
    api_client = Mock(spec=ClientCore)

    # Configure the mock API client to return the error response
    api_client.post.side_effect = DarwinException("Something went wrong")

    # Call the function being tested
    with pytest.raises(DarwinException):
        set_item_priority(
            api_client=api_client,
            team_slug="test-team",
            dataset_id=123,
            item_ids=[UUID("00000000-0000-0000-0000-000000000000")],
            priority=10,
        )
