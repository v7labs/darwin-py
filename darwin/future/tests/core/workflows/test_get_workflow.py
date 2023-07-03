from typing import List

import pytest
import responses
from pydantic import ValidationError
from sklearn import base

from darwin.future.core.client import Client
from darwin.future.core.workflows.get_workflow import get_workflow
from darwin.future.data_objects.workflow import Workflow
from darwin.future.tests.core.fixtures import *


@responses.activate
def test_get_workflows(base_client: Client, base_workflows_json: str) -> None:
    # Mocking the response using responses library
    response_data = base_workflows_json
    responses.add(
        responses.GET,
        f"{base_client.config.base_url}api/v2/teams/{base_client.config.default_team}/workflows/{id}",
        json=response_data,
        status=200,
    )

    # Call the function being tested
    workflow = get_workflow(base_client, "1")

    # Assertions
    assert isinstance(workflow, Workflow)

    # TODO: Probably not going to work!
    assert workflow.id == 1
    assert workflow.team_id == base_client.config.default_team


@responses.activate
def test_get_workflow_with_team_slug(base_client: Client, base_single_workflow_json: str) -> None:
    # Mocking the response using responses library
    team_slug = "team-slug"
    id = "1"

    response_data = base_single_workflow_json
    responses.add(
        responses.GET,
        f"{base_client.config.base_url}api/v2/teams/{team_slug}/workflows/{id}",
        json=response_data,
        status=200,
    )

    # Call the function being tested
    workflow = get_workflow(base_client, id, team_slug)

    # Assertions
    assert isinstance(workflow, Workflow)


@responses.activate
def test_get_workflows_with_invalid_response(base_client: Client) -> None:
    # Mocking the response using responses library
    # fmt: off
    responses.add(
        responses.GET,
        f"api/v2/teams/{base_client.config.default_team}/workflows/1",
        json=None,
        status=400
    )
    # fmt: on

    # Call the function being tested
    with pytest.raises(ValidationError):
        NON_EXISTENT_ID = "1"
        get_workflow(base_client, NON_EXISTENT_ID)
