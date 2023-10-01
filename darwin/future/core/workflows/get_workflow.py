from typing import List, Optional, Tuple

from pydantic import parse_obj_as

from darwin.future.core.client import ClientCore
from darwin.future.data_objects.workflow import WorkflowCore


def get_workflow(
    client: ClientCore, workflow_id: str, team_slug: Optional[str] = None
) -> Tuple[Optional[WorkflowCore], List[Exception]]:
    workflow: Optional[WorkflowCore] = None
    exceptions: List[Exception] = []

    try:
        team_slug = team_slug or client.config.default_team
        response = client.get(f"/v2/teams/{team_slug}/workflows/{workflow_id}")

        workflow = parse_obj_as(WorkflowCore, response)
    except Exception as e:
        exceptions.append(e)

    return workflow, exceptions
