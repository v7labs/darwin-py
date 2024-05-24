from requests import Session

from darwin.future.core.types.common import JSONType


def get_team_raw(session: Session, url: str) -> JSONType:
    """Gets the raw JSON response from a team endpoint

    Parameters:
        session (Session): Requests session to use
        url (str): URL to get

    Returns:
        JSONType: JSON response from the endpoint
    """
    response = session.get(url)
    response.raise_for_status()
    return response.json()
