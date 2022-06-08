from ctypes import cast
from typing import Any, Dict, Optional
from urllib import parse


def inject_default_team_slug(method):
    """
    Injects team_slug if not specified
    """

    def wrapper(self, *args, **kwargs):
        if "team_slug" not in kwargs:
            kwargs["team_slug"] = self._default_team
        return method(self, *args, **kwargs)

    return wrapper


class BackendV2:
    def __init__(self, client: "Client", default_team):
        self._client = client
        self._default_team = default_team

    @inject_default_team_slug
    def register_data(
        self, dataset_slug: str, payload: Dict[str, Any], *, team_slug: Optional[str] = None
    ) -> Dict[str, Any]:

        response = self._client._post(
            endpoint=f"v2/teams/{team_slug}/datasets/{dataset_slug}/items/register_upload",
            payload=payload,
            team_slug=team_slug,
        )
        return response

    @inject_default_team_slug
    def sign_upload(self, dataset_slug: str, upload_id: str, *, team_slug: Optional[str] = None) -> Dict[str, Any]:
        return self._client._get(
            f"v2/teams/{team_slug}/datasets/{dataset_slug}/items/sign_upload/{upload_id}", team_slug=team_slug
        )

    @inject_default_team_slug
    def confirm_upload(self, dataset_slug: str, upload_id: str, *, team_slug: Optional[str] = None) -> Dict[str, Any]:
        return self._client._put(
            f"v2/teams/{team_slug}/datasets/{dataset_slug}/items/confirm_upload/{upload_id}",
            payload={},
            team_slug=team_slug,
        )

    @inject_default_team_slug
    def fetch_items(
        self, dataset_id: int, cursor: Dict[str, Any], *, team_slug: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch the remote items from the given dataset.

        Parameters
        ----------
        dataset_id: int
            Id of the dataset the file belong to.
        cursor: Dict[str, Any]
            Number of items per page and page number. Defaults to {"page[size]": 500, "page[from]": 0}.
        payload: Dict[str, Any]
            Filter and sort parameters.
        team_slug: str
            The team slug of the dataset.

        Returns
        -------
         Dict[str, Any]
            A response dictionary with the file information.
        """

        cursor["dataset_ids"] = dataset_id

        return self._client._get(f"/v2/teams/{team_slug}/items?{parse.urlencode(cursor, True)}", team_slug)

    @inject_default_team_slug
    def archive_items(self, payload: Dict[str, Any], *, team_slug: Optional[str] = None) -> None:
        """
        Archives the item from the given dataset.

        Parameters
        ----------
        team_slug: str
            The slug of the team.
        payload: Dict[str, Any]
            A filter Dictionary that defines the items to be archived.
        """
        self._client._put(f"v2/teams/{team_slug}/items/archive", payload, team_slug)

    @inject_default_team_slug
    def restore_archived_items(self, payload: Dict[str, Any], *, team_slug: Optional[str] = None) -> None:
        """
        Restores the archived item from the given dataset.

        Parameters
        ----------
        team_slug: str
            The slug of the team.
        payload: Dict[str, Any]
            A filter Dictionary that defines the items to be restored.
        """
        self._client._put(f"v2/teams/{team_slug}/items/restore", payload, team_slug)
