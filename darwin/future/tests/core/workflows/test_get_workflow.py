import pytest
import responses
from pydantic import ValidationError
from requests import HTTPError

from darwin.future.core.client import Client, JSONType
from darwin.future.core.workflows.get_workflow import get_workflow
from darwin.future.data_objects.workflow import Workflow
from darwin.future.tests.core.fixtures import *


@responses.activate
def test_get_workflow(base_client: Client, base_single_workflow_object: JSONType) -> None:
    # Mocking the response using responses library
    response_data = base_single_workflow_object
    workflow_id = "1"
    responses.add(
        responses.GET,
        f"{base_client.config.base_url}api/v2/teams/{base_client.config.default_team}/workflows/{workflow_id}",
        json=response_data,
        status=200,
    )

    # Call the function being tested
    workflow, exceptions = get_workflow(base_client, workflow_id)

    # Assertions
    assert isinstance(workflow, Workflow)
    assert not exceptions


@responses.activate
def test_get_workflow_with_team_slug(base_client: Client, base_single_workflow_object: JSONType) -> None:
    # Mocking the response using responses library
    team_slug = "team-slug"
    workflow_id = "1"

    response_data = base_single_workflow_object
    responses.add(
        responses.GET,
        f"{base_client.config.base_url}api/v2/teams/{team_slug}/workflows/{workflow_id}",
        json=response_data,
        status=200,
    )

    # Call the function being tested
    workflow, exceptions = get_workflow(base_client, workflow_id, team_slug)

    # Assertions
    assert isinstance(workflow, Workflow)
    assert not exceptions


@responses.activate
def test_get_workflows_with_invalid_response(base_client: Client) -> None:
    # Mocking the response using responses library
    # fmt: off
    NON_EXISTENT_ID = "1"
    responses.add(
        responses.GET,
        f"{base_client.config.base_url}api/v2/teams/{base_client.config.default_team}/workflows/{NON_EXISTENT_ID}",
        json="{}",
        status=200
    )
    # fmt: on

    # Call the function being tested
    workflow, exceptions = get_workflow(base_client, NON_EXISTENT_ID)

    assert not workflow
    assert exceptions
    assert len(exceptions) == 1
    assert isinstance(exceptions[0], ValidationError)


@responses.activate
def test_get_workflows_with_error(base_client: Client) -> None:
    # Mocking the response using responses library
    # fmt: off
    NON_EXISTENT_ID = "1"
    responses.add(
        responses.GET,
        f"{base_client.config.base_url}api/v2/teams/{base_client.config.default_team}/workflows/{NON_EXISTENT_ID}",
        json="{}",
        status=400
    )
    # fmt: on

    workflow, exceptions = get_workflow(base_client, NON_EXISTENT_ID)

    assert not workflow
    assert exceptions
    assert len(exceptions) == 1
    assert isinstance(exceptions[0], HTTPError)
