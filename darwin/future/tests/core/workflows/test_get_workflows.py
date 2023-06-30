from cgi import test
from typing import List

import pytest
import responses
from pydantic import ValidationError

from darwin.future.core.client import Client
from darwin.future.core.workflows.get_workflows import get_workflows
from darwin.future.data_objects.workflow import Workflow

# TODO : Add in the test client fixture


def test_get_workflows(test_client: Client) -> None:
    # Mocking the response using responses library
    response_data = [{"id": 1, "name": "Workflow 1"}, {"id": 2, "name": "Workflow 2"}]
    responses.add(
        responses.GET,
        f"/api/v2/teams/{test_client.config.default_team}/workflows?worker=false",
        json=response_data,
        status=200,
    )

    # Call the function being tested
    workflows = get_workflows(test_client)

    # Assertions
    assert isinstance(workflows, List)
    assert len(workflows) == len(response_data)
    assert all(isinstance(workflow, Workflow) for workflow in workflows)


def test_get_workflows_with_team_slug(test_client: Client) -> None:
    # Mocking the response using responses library
    team_slug = "team-slug"
    response_data = [{"id": 1, "name": "Workflow 1"}, {"id": 2, "name": "Workflow 2"}]
    responses.add(responses.GET, f"/api/v2/teams/{team_slug}/workflows?worker=false", json=response_data, status=200)

    # Call the function being tested
    workflows = get_workflows(test_client, team_slug=team_slug)

    # Assertions
    assert isinstance(workflows, List)
    assert len(workflows) == len(response_data)
    assert all(isinstance(workflow, Workflow) for workflow in workflows)


def test_get_workflows_with_invalid_response(test_client: Client) -> None:
    # Mocking the response using responses library
    responses.add(
        responses.GET, f"/api/v2/teams/{test_client.config.default_team}/workflows?worker=false", json=None, status=200
    )

    # Call the function being tested
    with pytest.raises(ValidationError):
        get_workflows(test_client)
