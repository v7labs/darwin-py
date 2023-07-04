import pytest
import responses

from darwin.future.core.client import Client
from darwin.future.data_objects.workflow import Workflow
from darwin.future.meta.queries.workflow import WorkflowQuery
from darwin.future.tests.core.fixtures import *

WORKFLOWS_QUERY_ENDPOINT = "v2/workflows?worker=false"


@responses.activate
def test_workflowquery_collects_basic(base_client: Client, base_workflows_object: dict) -> None:
    query = WorkflowQuery()
    endpoint = base_client.config.api_endpoint + WORKFLOWS_QUERY_ENDPOINT
    responses.add(responses.GET, endpoint, json=base_workflows_object)
    workflows = query.collect(base_client)

    assert len(workflows) == 2
    assert all([isinstance(workflow, Workflow) for workflow in workflows])


@pytest.mark.todo("Implement test")
def test_workflowquery_only_passes_back_correctly_formed_objects() -> None:
    pytest.fail("Not implemented")


@pytest.mark.todo("Implement test")
def test_workflowquery_filters_uuid() -> None:
    pytest.fail("Not implemented")


@pytest.mark.todo("Implement test")
def test_workflowquery_filters_inserted_at() -> None:
    pytest.fail("Not implemented")


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
