from typing import Optional

from pydantic import parse_obj_as

from darwin.future.core.client import Client
from darwin.future.data_objects.workflow import Workflow


def get_workflow(client: Client, workflow_id: str, team_slug: Optional[str] = None) -> Workflow:
    team_slug = team_slug or client.config.default_team
    response = client.get(f"/v2/teams/{team_slug}/workflows/{workflow_id}")

    return parse_obj_as(Workflow, response)
