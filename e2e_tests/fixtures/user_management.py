import uuid
from typing import Any, Dict, Optional

import requests

from e2e_tests.logger_config import logger
from e2e_tests.objects import ConfigValues


def create_user(config: ConfigValues) -> Dict[str, Any]:
    """
    Create a user for testing

    Parameters
    ----------
    config : ConfigValues
        The config values to use

    Returns
    -------
    Dict[str, Any]
        User data including id, email, password, etc.
    """
    identifier = f"test-user-dpy-{uuid.uuid4().hex[:8]}"
    email = f"dpy+{identifier}+{uuid.uuid4().hex[:8]}@v7labs.com"
    password = "Password123"

    url = f"{config.server}/api/v2/fixtures/users"
    headers = {"Authorization": f"ApiKey {config.superadmin_api_key}"}
    payload = {
        "email": email,
        "first_name": identifier,
        "last_name": "Tester",
        "password": password,
    }

    logger.debug(f"Creating user {identifier} with email {email}")
    response = requests.post(url, json=payload, headers=headers)
    if not response.ok:
        raise Exception(f"Failed to create user: {response.text}")

    user_data = response.json()

    # Add authentication token to user data
    token = authenticate_user(config, email, password)
    user_data["token"] = token
    if token:
        silence_user_notifications(config, token)

    return user_data


def authenticate_user(config: ConfigValues, email: str, password: str) -> Optional[str]:
    """
    Authenticate a user and get their token

    Parameters
    ----------
    config : ConfigValues
        The config values to use
    email : str
        User email
    password : str
        User password

    Returns
    -------
    Optional[str]
        Authentication token if successful, None otherwise
    """
    logger.debug(f"Authenticating user {email}")
    auth_url = f"{config.server}/api/users/authenticate"
    auth_payload = {"email": email, "password": password}
    auth_response = requests.post(auth_url, json=auth_payload)

    if not auth_response.ok:
        logger.warning(f"Warning: Failed to authenticate user: {auth_response.text}")
        return None

    token = auth_response.json().get("token")
    if not token:
        logger.warning("Warning: No token found in authentication response")
        return None

    return token


def silence_user_notifications(config: ConfigValues, token: str) -> None:
    """
    Update user notification settings

    Parameters
    ----------
    config : ConfigValues
        The config values to use
    token : str
        User authentication token
    """
    logger.debug("Updating user notifications")
    profile_url = f"{config.server}/api/users/profile"
    headers = {"Authorization": f"Bearer {token}"}
    profile_payload = {"show_notifications": False}

    profile_response = requests.put(profile_url, json=profile_payload, headers=headers)
    if not profile_response.ok:
        logger.warning(
            f"Warning: Failed to update user notifications: {profile_response.text}"
        )
