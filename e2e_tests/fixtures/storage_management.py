from os import environ

import requests

from e2e_tests.logger_config import logger
from e2e_tests.objects import ConfigValues


def configure_external_storage(
    config_values: ConfigValues, team_slug: str, api_key: str
) -> None:
    """
    Configure external storage for a team

    Parameters
    ----------
    config_values : ConfigValues
        The config values to use
    """
    url = f"{config_values.server}/api/teams/{team_slug}/storage/"
    headers = {"Authorization": f"ApiKey {api_key}"}
    storage_name = environ.get("E2E_STORAGE_NAME")
    storage_region = environ.get("E2E_STORAGE_REGION")
    storage_bucket = environ.get("E2E_STORAGE_BUCKET")
    payload = {
        "default": False,
        "name": storage_name,
        "prefix": "",
        "readonly": False,
        "region": storage_region,
        "bucket": storage_bucket,
        "provider": "aws",
        "cloudfront_host": None,
    }

    logger.info(f"Configuring external storage for team {team_slug}")
    response = requests.post(url, json=payload, headers=headers)
    if not response.ok:
        raise Exception(f"Failed to configure external storage: {response.text}")
