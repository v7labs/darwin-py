from darwin.future.core.types import Client, Dataset, TeamSlug


def list_datasets(api_client: Client, team_slug: TeamSlug) -> None:
    response = api_client.get("/datasets")
