import requests
from e2e_tests.objects import ConfigValues, TeamConfigValues


def delete_workflows(
    team_config: TeamConfigValues, config_values: ConfigValues
) -> None:
    """
    Delete all workflows in a team

    Parameters
    ----------
    config : ConfigValues
        The config values to use
    team_slug : str
        The slug of the team
    """
    url = f"{config_values.server}/api/v2/teams/{team_config.team_slug}/workflows"
    headers = {"Authorization": f"ApiKey {team_config.api_key}"}

    response = requests.get(url, headers=headers)
    if not response.ok:
        raise Exception(f"Failed to get workflows: {response.text}")

    workflows = response.json()

    for workflow in workflows:
        workflow_id = workflow["id"]

        # First disconnect dataset if connected
        if workflow.get("dataset") and workflow["dataset"].get("id"):
            disconnect_url = f"{config_values.server}/api/v2/teams/{team_config.team_slug}/workflows/{workflow_id}/dataset"
            disconnect_response = requests.delete(disconnect_url, headers=headers)
            if not disconnect_response.ok:
                print(
                    f"Warning: Failed to disconnect dataset from workflow {workflow_id}: {disconnect_response.text}"
                )

        # Now delete the workflow
        delete_url = f"{config_values.server}/api/v2/teams/{team_config.team_slug}/workflows/{workflow_id}"
        delete_response = requests.delete(delete_url, headers=headers)
        if not delete_response.ok:
            print(
                f"Warning: Failed to delete workflow {workflow_id}: {delete_response.text}"
            )
    print("Deleted workflows")
