from requests import Session

from darwin.future.core.types.common import JSONType


def get_team_raw(session: Session, url: str) -> JSONType:
    """Returns the team with the given slug in raw JSON format"""
    response = session.get(url)
    response.raise_for_status()
    return response.json()
