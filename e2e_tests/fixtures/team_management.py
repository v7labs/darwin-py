import uuid
from typing import Any, Dict

import requests

from e2e_tests.fixtures.dataset_management import archive_datasets
from e2e_tests.fixtures.storage_management import configure_external_storage
from e2e_tests.fixtures.user_management import create_user
from e2e_tests.fixtures.workflow_management import delete_workflows
from e2e_tests.logger_config import logger
from e2e_tests.objects import ConfigValues, TeamConfigValues


def create_team_api_key(config: ConfigValues, team_id: str, user_token: str) -> str:
    """
    Create an API key for a team using the user's token

    Parameters
    ----------
    config : ConfigValues
        The config values to use
    team_id : str
        The ID of the team
    user_token : str
        The user's authentication token

    Returns
    -------
    str
        The created API key value
    """
    url = f"{config.server}/api/teams/{team_id}/api_keys"
    headers = {"Authorization": f"Bearer {user_token}"}

    # Full list of permissions
    permissions = [
        ["archive_team", "all"],
        ["transfer_team_ownership", "all"],
        ["manage_customer", "all"],
        ["update_team", "all"],
        ["view_team", "all"],
        ["view_datasets", "all"],
        ["export_dataset", "all"],
        ["create_dataset", "all"],
        ["update_dataset", "all"],
        ["archive_dataset", "all"],
        ["update_dataset_data", "all"],
        ["archive_dataset_items", "all"],
        ["delete_dataset_items", "all"],
        ["view_annotations", "all"],
        ["view_annotation_report", "all"],
        ["view_dataset_exports", "all"],
        ["view_dataset_report", "all"],
        ["view_annotation_classes", "all"],
        ["create_annotation_class", "all"],
        ["update_annotation_class", "all"],
        ["delete_annotation_class", "all"],
        ["import_annotations", "all"],
        ["assign_items", "all"],
        ["update_stage", "all"],
        ["create_comment_thread", "all"],
        ["create_comment", "all"],
        ["delete_comment_thread", "all"],
        ["delete_comment", "all"],
        ["update_comment_thread", "all"],
        ["update_comment", "all"],
        ["delete_membership", "all"],
        ["manage_invitations", "all"],
        ["update_membership", "all"],
        ["view_invitations", "all"],
        ["view_team_members", "all"],
        ["deploy_model", "all"],
        ["train_models", "all"],
        ["view_models", "all"],
        ["run_inference", "all"],
    ]

    payload = {
        "name": f"E2E Test Key {uuid.uuid4().hex[:8]}",
        "permissions": permissions,
    }

    logger.debug(f"Creating API key for team {team_id}")
    response = requests.post(url, json=payload, headers=headers)
    if not response.ok:
        raise Exception(f"Failed to create API key: {response.text}")

    api_key_data = response.json()
    return f'{api_key_data["prefix"]}.{api_key_data["value"]}'


def create_isolated_team(config: ConfigValues) -> Dict[str, Any]:
    """
    Create a team with a user as member and owner

    Parameters
    ----------
    config : ConfigValues
        The config values to use

    Returns
    -------
    Tuple[Dict[str, Any], Dict[str, Any]]
        Team data and user data
    """
    # First create a user
    user_data = create_user(config)

    # Create team with the user as owner
    team_name = f"dpy team {uuid.uuid4().hex[:8]}"
    url = f"{config.server}/api/v2/fixtures/teams"
    headers = {"Authorization": f"ApiKey {config.superadmin_api_key}"}
    payload = {
        "name": team_name,
        "owner_user_id": user_data["id"],
        "managed_status": "regular",
        "plan": "business",
        "partner_id": None,
    }

    logger.info(f"Creating team {team_name} with owner {user_data['id']}")
    response = requests.post(url, json=payload, headers=headers)
    if not response.ok:
        raise Exception(f"Failed to create team: {response.text}")

    team_data = response.json()

    # Create an API key for the team using the user's bearer token
    try:
        api_key = create_team_api_key(config, team_data["id"], user_data["token"])
        team_data["api_key"] = api_key

    except Exception as e:
        logger.warning(f"Warning: Failed to create API key for team: {str(e)}")

    configure_external_storage(config, team_data["slug"], api_key)

    logger.debug(f"Team created with slug: {team_data['slug']}")

    return team_data


def delete_isolated_team(
    team_config: TeamConfigValues, config_values: ConfigValues
) -> None:
    """
    Delete an isolated team after testing

    Parameters
    ----------
    config : ConfigValues
        The config values to use
    team_id : str
        The ID of the team to delete
    """
    # First clean up any resources in the team
    cleanup_team_resources(team_config, config_values)

    logger.debug(f"Archiving team {team_config.team_id}, {team_config.team_slug}")
    url = f"{config_values.server}/api/teams/{team_config.team_id}/archive"
    headers = {"Authorization": f"ApiKey {team_config.api_key}"}

    response = requests.put(url, headers=headers)
    if not response.ok:
        raise Exception(f"Failed to archive team: {response.text}")


def cleanup_team_resources(
    team_config: TeamConfigValues, config_values: ConfigValues
) -> None:
    """
    Clean up resources in a team before deletion

    Parameters
    ----------
    config : ConfigValues
        The config values to use
    team_id : str
        The ID of the team to clean up
    """
    archive_datasets(team_config, config_values)
    delete_workflows(team_config, config_values)
