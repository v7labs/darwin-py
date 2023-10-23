from unittest.mock import Mock

import pytest

from darwin.exceptions import DarwinException
from darwin.future.core.client import ClientCore
from darwin.future.core.items.set_priority import set_item_priority


def test_set_item_priority():
    # Create a mock API client
    api_client = Mock(spec=ClientCore)

    # Define the expected payload
    expected_payload = {"priority": 10}

    # Define the expected endpoint
    expected_endpoint = "/v2/teams/test-team/items/priority"

    # Define the expected response
    expected_response = {"status": "success"}

    # Configure the mock API client to return the expected response
    api_client.post.return_value = expected_response

    # Call the function being tested
    response = set_item_priority(
        api_client=api_client,
        team_slug="test-team",
        priority=10,
    )

    # Verify that the API client was called with the expected arguments
    api_client.post.assert_called_once_with(
        endpoint=expected_endpoint,
        data=expected_payload,
    )

    # Verify that the response matches the expected response
    assert response == expected_response


def test_set_item_priority_with_filters():
    # Create a mock API client
    api_client = Mock(spec=ClientCore)

    # Define the expected payload
    expected_payload = {
        "priority": 10,
        "filters": {"status": "open"},
    }

    # Define the expected endpoint
    expected_endpoint = "/v2/teams/test-team/items/priority"

    # Define the expected response
    expected_response = {"status": "success"}

    # Configure the mock API client to return the expected response
    api_client.post.return_value = expected_response

    # Call the function being tested
    response = set_item_priority(
        api_client=api_client,
        team_slug="test-team",
        priority=10,
        filters={"status": "open"},
    )

    # Verify that the API client was called with the expected arguments
    api_client.post.assert_called_once_with(
        endpoint=expected_endpoint,
        data=expected_payload,
    )

    # Verify that the response matches the expected response
    assert response == expected_response


def test_set_item_priority_with_error_response():
    # Create a mock API client
    api_client = Mock(spec=ClientCore)

    # Configure the mock API client to return the error response
    api_client.post.side_effect = DarwinException("Something went wrong")

    # Call the function being tested
    with pytest.raises(DarwinException):
        set_item_priority(
            api_client=api_client,
            team_slug="test-team",
            priority=10,
        )
