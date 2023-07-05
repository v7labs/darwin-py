from datetime import datetime

import pytest
import responses

from darwin.future.core.client import Client
from darwin.future.core.types.query import Modifier
from darwin.future.data_objects.workflow import Workflow
from darwin.future.meta.queries.workflow import WorkflowQuery
from darwin.future.tests.core.fixtures import *


def workflows_query_endpoint(team: str) -> str:
    return f"v2/teams/{team}/workflows?worker=false"


@responses.activate
def test_workflowquery_collects_basic(base_client: Client, base_filterable_workflows: dict) -> None:
    query = WorkflowQuery()
    endpoint = base_client.config.api_endpoint + workflows_query_endpoint(base_client.config.default_team)
    responses.add(responses.GET, endpoint, json=base_filterable_workflows)
    workflows = query.collect(base_client)

    assert len(workflows) == 3
    assert all([isinstance(workflow, Workflow) for workflow in workflows])


@responses.activate
def test_workflowquery_filters_uuid(base_client: Client, base_filterable_workflows: dict) -> None:
    query = WorkflowQuery().where(
        {
            "name": "uuid",
            "param": "6dca86a3-48fb-40cc-8594-88310f5f1fdf",
        }
    )
    endpoint = base_client.config.api_endpoint + workflows_query_endpoint(base_client.config.default_team)
    responses.add(responses.GET, endpoint, json=base_filterable_workflows)
    workflows = query.collect(base_client)

    assert len(workflows) == 1
    assert str(workflows[0].id) == "6dca86a3-48fb-40cc-8594-88310f5f1fdf"


@responses.activate
def test_workflowquery_filters_inserted_at(base_client: Client, base_filterable_workflows: dict) -> None:
    start = datetime.fromisoformat("2021-06-01T15:00:00.000000Z")
    end = datetime.fromisoformat("2021-06-04T15:00:00.000000Z")

    query = (
        WorkflowQuery()
        .where(
            {
                "name": "inserted_at",
                "modified": Modifier.GREATER_EQUAL,
                "param": start,
            }
        )
        .where(
            {
                "name": "inserted_at",
                "modifier": Modifier.LESS_EQUAL,
                "param": end,
            }
        )
    )
    endpoint = base_client.config.api_endpoint + workflows_query_endpoint(base_client.config.default_team)
    responses.add(responses.GET, endpoint, json=base_filterable_workflows)
    workflows = query.collect(base_client)

    assert len(workflows) == 2
    ids = [str(workflow.id) for workflow in workflows]
    assert "53d2c997-6bb0-4766-803c-3c8d1fb21072" in ids
    assert "6dca86a3-48fb-40cc-8594-88310f5f1fdf" in ids


@pytest.mark.todo("Implement test")
def test_workflowquery_filters_updated_at() -> None:
    pytest.fail("Not implemented")


@pytest.mark.todo("Implement test")
def test_workflowquery_filters_dataset_slug() -> None:
    pytest.fail("Not implemented")


@pytest.mark.todo("Implement test")
def test_workflowquery_filters_dataset_id() -> None:
    pytest.fail("Not implemented")


# ? Needed?
@pytest.mark.todo("Implement test")
def test_workflowquery_filters_dataset_name() -> None:
    pytest.fail("Not implemented")


# ? Needed?
@pytest.mark.todo("Implement test")
def test_workflowquery_filters_stages() -> None:
    pytest.fail("Not implemented")
