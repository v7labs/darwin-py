import argparse
from pathlib import Path
from typing import Optional

from darwin.cli_functions import authenticate
from darwin.client import Client
from darwin.dataset.identifier import DatasetIdentifier
from darwin.dataset.utils import split_dataset


def run_demo(
    *,
    team_slug: Optional[str],
    dataset_slug: Optional[str] = None,
    datasets_dir: Optional[str] = None,
    api_key: Optional[str] = None,
    config_path: Optional[Path] = None,
):
    """
    Download a Darwin dataset on the file system.

    Parameters
    ----------
    team_slug : str
        Slug of the team to select
    dataset_slug : str
        This is the dataset name with everything lower-case, removed specials characters and
        spaces are replaced by dashes, e.g., `bird-species`. This string is unique within a team
    datasets_dir : Path
        Path where the client should be initialized from (aka the root path)
    api_key: str
        API key to authenticate the client
    config_path: Path
        Path to a configuration path which contains the authentication information to use

    Returns
    -------
    splits : dict
        Keys are the different splits (random, tags, ...) and values are the relative file names
    """
    # Authenticate the new KEY if available
    if api_key is not None:
        authenticate(api_key=api_key, default_team=True, datasets_dir=datasets_dir)
    # Get the client used to perform remote operations
    if config_path is not None:
        client = Client.from_config(config_path=config_path)
    else:
        client = Client.local(team_slug=team_slug)
    # Create a dataset identifier
    dataset_identifier = DatasetIdentifier.from_slug(dataset_slug=dataset_slug, team_slug=team_slug)
    # Get an object representing the remote dataset
    ds = client.get_remote_dataset(dataset_identifier=dataset_identifier)
    # Download the dataset on the local file system
    ds.pull()
    # Split the dataset in train/val/test
    splits = split_dataset(dataset=ds)
    # Here you can start your Machine Learning model :)


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="This script can be used to download a dataset from Darwin",
    )
    parser.add_argument(
        "--datasets-dir", help="Path to where the dataset will be downloaded", default=None, type=Path,
    )
    parser.add_argument("--dataset-slug", help="Dataset slug (see Darwin documentation)", default=None, type=str)
    parser.add_argument("--team-slug", help="Team slug (see Darwin documentation)", default=None, type=str)
    parser.add_argument("--api-key", help="API key to authenticate the client", default=None, type=str)
    parser.add_argument(
        "--config-path", help="Path to the configuration file to authenticate the client", default=None, type=Path,
    )
    args = parser.parse_args()

    # Run the actual code
    run_demo(**args.__dict__)
