from typing import List

import responses
from pydantic import ValidationError

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONType
from darwin.future.core.workflows import list_workflows
from darwin.future.data_objects.workflow import WorkflowCore
from darwin.future.exceptions import BadRequest
from darwin.future.tests.core.fixtures import *


@responses.activate
def test_list_workflows(base_client: ClientCore, base_workflows_object: str) -> None:
    # Mocking the response using responses library
    response_data = base_workflows_object
    responses.add(
        responses.GET,
        f"{base_client.config.base_url}api/v2/teams/{base_client.config.default_team}/workflows?worker=false",
        json=response_data,
        status=200,
    )

    # Call the function being tested
    workflows, exceptions = list_workflows(base_client)

    # Assertions
    assert isinstance(workflows, List)
    assert len(workflows) == 3
    assert all(isinstance(workflow, WorkflowCore) for workflow in workflows)

    assert not exceptions


@responses.activate
def test_list_workflows_with_team_slug(
    base_client: ClientCore, base_workflows_object: JSONType
) -> None:
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
    workflows, exceptions = list_workflows(base_client, team_slug=team_slug)

    # Assertions
    assert isinstance(workflows, List)
    assert len(workflows) == len(response_data)
    assert all(isinstance(workflow, WorkflowCore) for workflow in workflows)

    assert not exceptions


@responses.activate
def test_list_workflows_with_invalid_response(base_client: ClientCore) -> None:
    # Mocking the response using responses library
    responses.add(
        responses.GET,
        f"{base_client.config.base_url}api/v2/teams/{base_client.config.default_team}/workflows?worker=false",
        json="INVALIDRESPONSE",
        status=200,
    )

    # Call the function being tested
    workflows, exceptions = list_workflows(base_client)

    assert isinstance(exceptions, List)
    assert len(exceptions) == 1
    assert isinstance(exceptions[0], ValidationError)

    assert not workflows


@responses.activate
def test_list_workflows_with_error(base_client: ClientCore) -> None:
    # Mocking the response using responses library
    responses.add(
        responses.GET,
        f"{base_client.config.base_url}api/v2/teams/{base_client.config.default_team}/workflows?worker=false",
        json="",
        status=400,
    )

    # Call the function being tested
    workflows, exceptions = list_workflows(base_client)

    assert isinstance(exceptions, List)
    assert len(exceptions) == 1
    assert isinstance(exceptions[0], BadRequest)

    assert not workflows
