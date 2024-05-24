from typing import Optional

from darwin.future.core.client import ClientCore
from darwin.future.data_objects.workflow import WorkflowCore


def get_workflow(
    client: ClientCore, workflow_id: str, team_slug: Optional[str] = None
) -> WorkflowCore:
    """
    Retrieves a workflow by ID from the Darwin API.

    Parameters:
    -----------
    client : ClientCore
        The Darwin API client to use for the request.
    workflow_id : str
        The ID of the workflow to retrieve.
    team_slug : Optional[str]
        The slug of the team that owns the workflow. If not provided, the default team from the client's configuration
        will be used.

    Returns:
    --------
    WorkflowCore
        The retrieved workflow, as a WorkflowCore object.

    Raises:
    -------
    HTTPError
        If the API returns an error response.
    ValidationError
        If the API response does not match the expected schema.
    """
    team_slug = team_slug or client.config.default_team
    response = client.get(f"/v2/teams/{team_slug}/workflows/{workflow_id}")
    assert isinstance(response, dict)
    return WorkflowCore.model_validate(response)
