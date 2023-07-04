from typing import List

import pytest
import responses
from pydantic import ValidationError
from requests import HTTPError

from darwin.future.core.client import Client, JSONType
from darwin.future.core.workflows.get_workflows import get_workflows
from darwin.future.data_objects.workflow import Workflow
from darwin.future.tests.core.fixtures import *


@responses.activate
def test_get_workflows(base_client: Client, base_workflows_object: str) -> None:
    # Mocking the response using responses library
    response_data = base_workflows_object
    responses.add(
        responses.GET,
        f"{base_client.config.base_url}api/v2/teams/{base_client.config.default_team}/workflows?worker=false",
        json=response_data,
        status=200,
    )

    # Call the function being tested
    workflows = get_workflows(base_client)

    # Assertions
    assert isinstance(workflows, List)
    assert len(workflows) == 3
    assert all(isinstance(workflow, Workflow) for workflow in workflows)


@responses.activate
def test_get_workflows_with_team_slug(base_client: Client, base_workflows_object: JSONType) -> None:
    # Mocking the response using responses library
    team_slug = "team-slug"
    response_data = base_workflows_object
    responses.add(
        responses.GET,
        f"{base_client.config.base_url}api/v2/teams/{team_slug}/workflows?worker=false",
        json=response_data,
        status=200,
    )

    # Call the function being tested
    workflows = get_workflows(base_client, team_slug=team_slug)

    # Assertions
    assert isinstance(workflows, List)
    assert len(workflows) == len(response_data)
    assert all(isinstance(workflow, Workflow) for workflow in workflows)


@responses.activate
def test_get_workflows_with_invalid_response(base_client: Client) -> None:
    # Mocking the response using responses library
    responses.add(
        responses.GET,
        f"{base_client.config.base_url}api/v2/teams/{base_client.config.default_team}/workflows?worker=false",
        json="{}",
        status=200,
    )

    # Call the function being tested
    with pytest.raises(ValidationError):
        get_workflows(base_client)


@responses.activate
def test_get_workflows_with_error(base_client: Client) -> None:
    # Mocking the response using responses library
    responses.add(
        responses.GET,
        f"{base_client.config.base_url}api/v2/teams/{base_client.config.default_team}/workflows?worker=false",
        json="",
        status=400,
    )

    # Call the function being tested
    with pytest.raises(HTTPError):
        get_workflows(base_client)
