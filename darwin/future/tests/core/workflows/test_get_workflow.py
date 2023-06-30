from typing import List, Optional

import pytest
import responses
from pydantic import ValidationError
from requests.exceptions import HTTPError

from darwin.future.core.client import Client
from darwin.future.core.workflows.get_workflows import get_workflows
from darwin.future.data_objects.workflow import Workflow
from darwin.future.tests.fixtures import (
    create_workflow_data,  # TODO Create this function
)

# FIXME


@responses.activate
def test_get_workflows(client: Client) -> None:
    # Mocking the response using responses library
    response_data = [create_workflow_data(name="Workflow 1"), create_workflow_data(name="Workflow 2")]
    responses.add(
        responses.GET,
        f"/api/v2/teams/{client.config.default_team}/workflows?worker=false",
        json=response_data,
        status=200,
    )

    # Call the function being tested
    workflows = get_workflows(client)

    # Assertions
    assert isinstance(workflows, List)
    assert len(workflows) == len(response_data)
    assert all(isinstance(workflow, Workflow) for workflow in workflows)


@responses.activate
def test_get_workflows_with_team_slug(client: Client) -> None:
    # Mocking the response using responses library
    team_slug = "team-slug"
    response_data = [create_workflow_data(name="Workflow 1"), create_workflow_data(name="Workflow 2")]
    responses.add(responses.GET, f"/api/v2/teams/{team_slug}/workflows?worker=false", json=response_data, status=200)

    # Call the function being tested
    workflows = get_workflows(client, team_slug=team_slug)

    # Assertions
    assert isinstance(workflows, List)
    assert len(workflows) == len(response_data)
    assert all(isinstance(workflow, Workflow) for workflow in workflows)


@responses.activate
def test_get_workflows_with_invalid_response(client: Client) -> None:
    # Mocking the response using responses library
    responses.add(
        responses.GET, f"/api/v2/teams/{client.config.default_team}/workflows?worker=false", json=None, status=200
    )

    # Call the function being tested
    with pytest.raises(ValidationError):
        get_workflows(client)
