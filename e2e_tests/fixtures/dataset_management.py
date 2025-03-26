import requests

from e2e_tests.objects import ConfigValues, TeamConfigValues


def archive_datasets(
    team_config: TeamConfigValues, config_values: ConfigValues
) -> None:
    """
    Archive all datasets in a team

    Parameters
    ----------
    config : ConfigValues
        The config values to use
    team_slug : str
        The slug of the team
    """
    url = f"{config_values.server}/api/datasets"
    headers = {"Authorization": f"ApiKey {team_config.api_key}"}

    response = requests.get(url, headers=headers)
    if not response.ok:
        raise Exception(f"Failed to get datasets: {response.text}")

    datasets = response.json()

    for dataset in datasets:
        dataset_id = dataset["id"]
        archive_url = f"{config_values.server}/api/datasets/{dataset_id}/archive"
        archive_response = requests.put(archive_url, headers=headers)
        if not archive_response.ok:
            print(
                f"Warning: Failed to delete dataset {dataset_id}: {archive_response.text}"
            )
    print("Archived datasets")
