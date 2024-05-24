from typing import List, Optional

from darwin.future.core.client import ClientCore
from darwin.future.data_objects.workflow import WorkflowCore


def get_workflows(
    client: ClientCore, team_slug: Optional[str] = None
) -> List[WorkflowCore]:
    team_slug = team_slug or client.config.default_team
    response = client.get(f"/v2/teams/{team_slug}/workflows?worker=false")
    assert isinstance(response, list)
    assert all(isinstance(workflow, dict) for workflow in response)
    assert len(response) > 0, "No workflows found"
    return [WorkflowCore.model_validate(workflow) for workflow in response]
