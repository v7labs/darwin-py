import argparse
import datetime
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Union

import humanize

import darwin.exporter as exporter
import darwin.exporter.formats
import darwin.importer as importer
import darwin.importer.formats
from darwin.client import Client
from darwin.config import Config
from darwin.dataset.identifier import DatasetIdentifier
from darwin.dataset.utils import get_release_path, split_dataset
from darwin.exceptions import (
    InvalidLogin,
    MissingConfig,
    NameTaken,
    NotFound,
    Unauthenticated,
    UnsupportedExportFormat,
    UnsupportedFileType,
    ValidationError,
)
from darwin.table import Table
from darwin.utils import find_files, persist_client_configuration, prompt, secure_continue_request


def validate_api_key(api_key: str):
    example_key = "DHMhAWr.BHucps-tKMAi6rWF1xieOpUvNe5WzrHP"

    if len(api_key) != 40:
        _error(f"Expected key to be 40 characters long\n(example: {example_key})")

    if "." not in api_key:
        _error(f"Expected key formatted as prefix . suffix\n(example: {example_key})")

    if len(api_key.split(".")[0]) != 7:
        _error(f"Expected key prefix to be 7 characters long\n(example: {example_key})")


def authenticate(api_key: str, default_team: Optional[bool] = None, datasets_dir: Optional[Path] = None) -> Config:
    """Authenticate the API key against the server and creates a configuration file for it

    Parameters
    ----------
    api_key : str
        API key to use for the client login
    default_team: bool
        Flag to make the team the default one
    datasets_dir: Path
        Dataset directory on the file system

    Returns
    -------
    Config
    A configuration object to handle YAML files
    """
    # Resolve the home folder if the dataset_dir starts with ~ or ~user

    validate_api_key(api_key)

    try:
        client = Client.from_api_key(api_key=api_key)
        config_path = Path.home() / ".darwin" / "config.yaml"
        config_path.parent.mkdir(exist_ok=True)

        if default_team is None:
            default_team = input(f"Make {client.default_team} the default team? [y/N] ") in ["Y", "y"]
        if datasets_dir is None:
            datasets_dir = prompt("Datasets directory", "~/.darwin/datasets")

        datasets_dir = Path(datasets_dir).expanduser()
        Path(datasets_dir).mkdir(parents=True, exist_ok=True)

        client.set_datasets_dir(datasets_dir)

        default_team = client.default_team if default_team else None
        return persist_client_configuration(client, default_team=default_team)

    except InvalidLogin:
        _error("Invalid API key")


def current_team():
    """Print the team currently authenticated against"""
    client = _load_client()
    print(client.default_team)


def list_teams():
    """Print a table of teams to which the client belong to"""
    for team in _config().get_all_teams():
        if team["default"]:
            print(f"{team['slug']} (default)")
        else:
            print(team["slug"])


def set_team(team_slug: str):
    """Switches the client to the selected team and persist the change on the configuration file

    Parameters
    ----------
    team_slug : str
        Slug of the team to switch to
    """

    config = _config()
    config.set_default_team(team_slug)


def create_dataset(dataset_slug: str):
    """Creates a dataset remotely"""
    identifier = DatasetIdentifier.parse(dataset_slug)
    client = _load_client(team_slug=identifier.team_slug)
    try:
        dataset = client.create_dataset(name=identifier.dataset_slug)
        print(
            f"Dataset '{dataset.name}' ({dataset.team}/{dataset.slug}) has been created.\nAccess at {dataset.remote_path}"
        )
    except NameTaken:
        _error(f"Dataset name '{identifier.dataset_slug}' is already taken.")
    except ValidationError:
        _error(f"Dataset name '{identifier.dataset_slug}' is not valid.")


def local(team: Optional[str] = None):
    """Lists synced datasets, stored in the specified path. """
    table = Table(["name", "images", "sync_date", "size"], [Table.L, Table.R, Table.R, Table.R])
    client = _load_client(offline=True)
    for dataset_path in client.list_local_datasets(team=team):
        table.add_row(
            {
                "name": f"{dataset_path.parent.name}/{dataset_path.name}",
                "images": sum(1 for _ in find_files([dataset_path])),
                "sync_date": humanize.naturaldate(datetime.datetime.fromtimestamp(dataset_path.stat().st_mtime)),
                "size": humanize.naturalsize(sum(p.stat().st_size for p in find_files([dataset_path]))),
            }
        )
    # List deprecated datasets
    deprecated_local_datasets = client.list_deprecated_local_datasets()
    if deprecated_local_datasets:
        for dataset_path in client.list_deprecated_local_datasets():
            table.add_row(
                {
                    "name": dataset_path.name + " (deprecated format)",
                    "images": sum(1 for _ in find_files([dataset_path])),
                    "sync_date": humanize.naturaldate(datetime.datetime.fromtimestamp(dataset_path.stat().st_mtime)),
                    "size": humanize.naturalsize(sum(p.stat().st_size for p in find_files([dataset_path]))),
                }
            )

    print(table)
    if len(list(deprecated_local_datasets)):
        print(
            f"\nWARNING: found some local datasets that use a deprecated format "
            f"not supported by the recent version of darwin-py. "
            f"Run `darwin dataset migrate team_slug/dataset_slug` "
            "if you want to be able to use them in darwin-py."
        )


def path(dataset_slug: str) -> Path:
    """Returns the absolute path of the specified dataset, if synced"""
    identifier = DatasetIdentifier.parse(dataset_slug)
    client = _load_client(offline=True)

    for p in client.list_local_datasets(team=identifier.team_slug):
        if identifier.dataset_slug == p.name:
            return p

    for p in client.list_deprecated_local_datasets(team=identifier.team_slug):
        if identifier.dataset_slug == p.name:
            _error(
                f"Found a local version of the dataset {identifier.dataset_slug} which uses a deprecated format. "
                f"Run `darwin dataset migrate {identifier}` if you want to be able to use it in darwin-py."
                f"\n{p} (deprecated format)"
            )

    _error(
        f"Dataset '{identifier.dataset_slug}' does not exist locally. "
        f"Use 'darwin dataset remote' to see all the available datasets, "
        f"and 'darwin dataset pull' to pull them."
    )


def url(dataset_slug: str) -> Path:
    """Returns the url of the specified dataset"""
    client = _load_client(offline=True)
    try:
        remote_dataset = client.get_remote_dataset(dataset_identifier=dataset_slug)
        print(remote_dataset.remote_path)
    except NotFound as e:
        _error(f"Dataset '{e.name}' does not exist.")


def dataset_report(dataset_slug: str, granularity) -> Path:
    """Returns the url of the specified dataset"""
    client = _load_client(offline=True)
    try:
        remote_dataset = client.get_remote_dataset(dataset_identifier=dataset_slug)
        report = remote_dataset.get_report(granularity)
        print(report)
    except NotFound:
        _error(f"Dataset '{dataset_slug}' does not exist.")


def export_dataset(
    dataset_slug: str, include_url_token: bool, annotation_class_ids: Optional[List] = None, name: Optional[str] = None
):
    """Create a new release for the dataset

    Parameters
    ----------
    dataset_slug: str
        Slug of the dataset to which we perform the operation on
    annotation_class_ids: List
        List of the classes to filter
    name: str
        Name of the release
    """
    client = _load_client(offline=False)
    identifier = DatasetIdentifier.parse(dataset_slug)
    ds = client.get_remote_dataset(identifier)
    ds.export(annotation_class_ids=annotation_class_ids, name=name, include_url_token=include_url_token)
    identifier.version = name
    print(f"Dataset {dataset_slug} successfully exported to {identifier}")


def pull_dataset(dataset_slug: str, only_annotations: bool = False, folders: bool = False, video_frames: bool = False):
    """Downloads a remote dataset (images and annotations) in the datasets directory.

    Parameters
    ----------
    dataset_slug: str
        Slug of the dataset to which we perform the operation on
    only_annotations: bool
        Download only the annotations and no corresponding images
    folders: bool
        Recreates the folders in the dataset
    video_frames: bool
        Pulls video frames images instead of video files
    """
    version = DatasetIdentifier.parse(dataset_slug).version or "latest"
    client = _load_client(offline=False, maybe_guest=True)
    try:
        dataset = client.get_remote_dataset(dataset_identifier=dataset_slug)
    except NotFound:
        _error(
            f"Dataset '{dataset_slug}' does not exist, please check the spelling. "
            f"Use 'darwin remote' to list all the remote datasets."
        )
    except Unauthenticated:
        _error(f"please re-authenticate")
    try:
        release = dataset.get_release(version)
        dataset.pull(release=release, only_annotations=only_annotations, use_folders=folders, video_frames=video_frames)
    except NotFound:
        _error(
            f"Version '{dataset.identifier}:{version}' does not exist "
            f"Use 'darwin dataset releases' to list all available versions."
        )
    except UnsupportedExportFormat as uef:
        _error(
            f"Version '{dataset.identifier}:{version}' is of format '{uef.format}', "
            f"only the darwin format ('json') is supported for `darwin dataset pull`"
        )
    print(f"Dataset {release.identifier} downloaded at {dataset.local_path}. ")


def migrate_dataset(dataset_slug: str):
    """Migrates an outdated local dataset to the latest format.

    Parameters
    ----------
    dataset_slug: str
        Slug of the dataset to which we perform the operation on
    """
    identifier = DatasetIdentifier.parse(dataset_slug)
    if not identifier.team_slug:
        _error("Team name missing.\nUsage: darwin dataset migrate <team-name>/<dataset-name>")

    client = _load_client(offline=True)
    authenticated_teams = [e["slug"] for e in client.config.get_all_teams()]
    if identifier.team_slug not in authenticated_teams:
        _error(
            f"Could not find '{identifier.team_slug}' in the authenticated teams. "
            "Run 'darwin authenticate' to authenticate it."
        )

    for p in client.list_local_datasets(team=identifier.team_slug):
        if identifier.dataset_slug == p.name:
            print(f"Dataset '{dataset_slug}' already migrated.")
            return

    old_path = None
    for p in client.list_deprecated_local_datasets(identifier.team_slug):
        if identifier.dataset_slug == p.name:
            old_path = p
    if not old_path:
        _error(
            f"Could not find a deprecated local version of the dataset '{dataset_slug}'. "
            f"Use 'darwin dataset pull {dataset_slug}' to pull the latest version from darwin."
        )

    # Move the dataset under the team_slug folder
    team_config = client.config.get_team(identifier.team_slug)
    team_path = Path(team_config["datasets_dir"]) / identifier.team_slug
    team_path.mkdir(exist_ok=True)
    shutil.move(str(old_path), str(team_path))

    # Update internal structure
    dataset_path = team_path / old_path.name
    release_path = dataset_path / "releases/migrated"
    for p in ["annotations", "lists"]:
        if (dataset_path / p).exists():
            shutil.move(str(dataset_path / p), str(release_path / p))

    latest_release = dataset_path / "releases/latest"
    if latest_release.exists():
        latest_release.unlink()
    latest_release.symlink_to("./migrated")

    print(f"Dataset {identifier.dataset_slug} migrated to {dataset_path}.")


def split(dataset_slug: str, val_percentage: float, test_percentage: float, seed: Optional[int] = 0):
    """Splits a local version of a dataset into train, validation, and test partitions

    Parameters
    ----------
    dataset_slug: str
        Slug of the dataset to which we perform the operation on
    val_percentage: float
        Percentage in the validation set
    test_percentage: float
        Percentage in the test set
    seed: int
        Random seed
    """
    identifier = DatasetIdentifier.parse(dataset_slug)
    client = _load_client(offline=True)

    for p in client.list_local_datasets(team=identifier.team_slug):
        if identifier.dataset_slug == p.name:
            try:
                split_path = split_dataset(
                    dataset_path=p,
                    release_name=identifier.version,
                    val_percentage=val_percentage,
                    test_percentage=test_percentage,
                    split_seed=seed,
                )
                print(f"Partition lists saved at {split_path}")
                return
            except NotFound as e:
                _error(e.name)
            except ValueError as e:
                _error(e.args[0])

    for p in client.list_deprecated_local_datasets(team=identifier.team_slug):
        if identifier.dataset_slug == p.name:
            _error(
                f"Found a local version of the dataset {identifier.dataset_slug} which uses a deprecated format. "
                f"Run `darwin dataset migrate {identifier}` if you want to be able to use it in darwin-py."
            )

    _error(
        f"Dataset '{identifier.dataset_slug}' does not exist locally. "
        f"Use 'darwin dataset remote' to see all the available datasets, "
        f"and 'darwin dataset pull' to pull them."
    )


def list_remote_datasets(all_teams: bool, team: Optional[str] = None):
    """Lists remote datasets with its annotation progress"""
    # TODO: add listing open datasets
    table = Table(["name", "images"], [Table.L, Table.R])
    datasets = []
    if all_teams:
        for team in _config().get_all_teams():
            client = _load_client(team["slug"])
            datasets += client.list_remote_datasets()
    else:
        client = _load_client(team)
        datasets = client.list_remote_datasets()

    for dataset in datasets:
        table.add_row({"name": f"{dataset.team}/{dataset.slug}", "images": dataset.image_count})
    if len(table) == 0:
        print("No dataset available.")
    else:
        print(table)


def remove_remote_dataset(dataset_slug: str):
    """Remove a remote dataset from the workview. The dataset gets archived. """
    client = _load_client(offline=False)
    try:
        dataset = client.get_remote_dataset(dataset_identifier=dataset_slug)
        print(f"About to delete {dataset.identifier} on darwin.")
        if not secure_continue_request():
            print("Cancelled.")
            return

        dataset.remove_remote()
    except NotFound:
        _error(f"No dataset with name '{dataset_slug}'")


def dataset_list_releases(dataset_slug: str):
    client = _load_client(offline=False)
    try:
        dataset = client.get_remote_dataset(dataset_identifier=dataset_slug)
        releases = dataset.get_releases()
        if len(releases) == 0:
            print("No available releases, export one first.")
            return
        table = Table(["name", "images", "classes", "export_date"], [Table.L, Table.R, Table.R, Table.R])
        for release in releases:
            if not release.available:
                continue
            table.add_row(
                {
                    "name": release.identifier,
                    "images": release.image_count,
                    "classes": release.class_count,
                    "export_date": release.export_date,
                }
            )
        print(table)
    except NotFound:
        _error(f"No dataset with name '{dataset_slug}'")


def upload_data(
    dataset_slug: str,
    files: Optional[List[str]],
    files_to_exclude: Optional[List[str]],
    fps: int,
    path: Optional[str],
    frames: Optional[bool],
):
    """Uploads the files provided as parameter to the remote dataset selected

    Parameters
    ----------
    dataset_slug : str
        Slug of the dataset to retrieve
    files : list[str]
        List of files to upload. Can be None.
    files_to_exclude : list[str]
        List of files to exclude from the file scan (which is done only if files is None)
    fps : int
        Frame rate to split videos in

    Returns
    -------
    generator : function
            Generator for doing the actual uploads. This is None if blocking is True
    count : int
        The files count
    """
    client = _load_client()
    try:
        dataset = client.get_remote_dataset(dataset_identifier=dataset_slug)
        dataset.push(files_to_exclude=files_to_exclude, fps=fps, as_frames=frames, files_to_upload=files, path=path)
    except NotFound as e:
        _error(f"No dataset with name '{e.name}'")
    except UnsupportedFileType as e:
        _error(f"Unsupported file type {e.path.suffix} ({e.path.name})")
    except ValueError:
        _error(f"No files found")


def dataset_import(dataset_slug, format, files):
    client = _load_client(dataset_identifier=dataset_slug)
    parser = find_supported_format(format, darwin.importer.formats.supported_formats)

    try:
        dataset = client.get_remote_dataset(dataset_identifier=dataset_slug)
        importer.import_annotations(dataset, parser, files)
    except NotFound as e:
        _error(f"No dataset with name '{e.name}'")


def list_files(dataset_slug: str, statuses: str, path: str, only_filenames: bool):
    client = _load_client(dataset_identifier=dataset_slug)
    try:
        dataset = client.get_remote_dataset(dataset_identifier=dataset_slug)
        filters = {}
        if statuses:
            for status in statuses.split(","):
                if status not in ["new", "annotate", "review", "complete", "archived"]:
                    _error(f"Invalid status '{status}', available statuses: annotate, archived, complete, new, review")
            filters["statuses"] = statuses
        else:
            filters["statuses"] = "new,annotate,review,complete"
        if path:
            filters["path"] = path
        for file in dataset.fetch_remote_files(filters):
            if only_filenames:
                print(file.filename)
            else:
                image_url = dataset.workview_url_for_item(file)
                print(f"{file.filename}\t{file.status if not file.archived else 'archived'}\t {image_url}")
    except NotFound as e:
        _error(f"No dataset with name '{e.name}'")


def set_file_status(dataset_slug: str, status: str, files: List[str]):
    if status not in ["archived", "restore-archived"]:
        _error(f"Invalid status '{status}', available statuses: archived, restore-archived")

    client = _load_client(dataset_identifier=dataset_slug)
    try:
        dataset = client.get_remote_dataset(dataset_identifier=dataset_slug)
        items = dataset.fetch_remote_files({"filenames": ",".join(files)})
        if status == "archived":
            dataset.archive(items)
        elif status == "restore-archived":
            dataset.restore_archived(items)
    except NotFound as e:
        _error(f"No dataset with name '{e.name}'")


def find_supported_format(query, supported_formats):
    for (fmt, fmt_parser) in supported_formats:
        if fmt == query:
            return fmt_parser
    list_of_formats = ", ".join([fmt for fmt, _ in supported_formats])
    _error(f"Unsupported format, currently supported: {list_of_formats}")


def dataset_convert(dataset_slug: str, format: str, output_dir: Optional[Union[str, Path]]):
    client = _load_client()
    parser = find_supported_format(format, darwin.exporter.formats.supported_formats)

    try:
        dataset = client.get_remote_dataset(dataset_identifier=dataset_slug)
        if not dataset.local_path.exists():
            _error(
                f"No annotations downloaded for dataset f{dataset}, first pull a release using "
                f"'darwin dataset pull {dataset_slug}'"
            )

        release_path = get_release_path(dataset.local_path)
        annotations_path = release_path / "annotations"
        if output_dir is None:
            output_dir = release_path / "other_formats" / f"{format}"
        else:
            output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        exporter.export_annotations(parser, [annotations_path], output_dir)
    except NotFound as e:
        _error(f"No dataset with name '{e.name}'")


def convert(format, files, output_dir):
    parser = find_supported_format(format, darwin.exporter.formats.supported_formats)
    exporter.export_annotations(parser, files, output_dir)


def help(parser, subparser: Optional[str] = None):
    if subparser:
        parser = next(
            action.choices[subparser]
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction) and subparser in action.choices
        )

    actions = [action for action in parser._actions if isinstance(action, argparse._SubParsersAction)]

    print(parser.description)
    print("\nCommands:")
    for action in actions:
        # get all subparsers and print help
        for choice in sorted(action._choices_actions, key=lambda x: x.dest):
            print("    {:<19} {}".format(choice.dest, choice.help))


def _error(message):
    print(f"Error: {message}")
    sys.exit(1)


def _config():
    return Config(Path.home() / ".darwin" / "config.yaml")


def _load_client(
    team_slug: Optional[str] = None,
    offline: bool = False,
    maybe_guest: bool = False,
    dataset_identifier: Optional[str] = None,
):
    """Fetches a client, potentially offline

    Parameters
    ----------
    offline : bool
        Flag for using an offline client

    maybe_guest : bool
        Flag to make a guest client, if config is missing
    Returns
    -------
    Client
    The client requested
    """
    if not team_slug and dataset_identifier:
        team_slug = DatasetIdentifier.parse(dataset_identifier).team_slug
    try:
        config_dir = Path.home() / ".darwin" / "config.yaml"
        client = Client.from_config(config_dir, team_slug=team_slug)
        return client
    except MissingConfig:
        if maybe_guest:
            return Client.from_guest()
        else:
            _error("Authenticate first")
    except InvalidLogin:
        _error("Please re-authenticate")
    except Unauthenticated:
        _error("Please re-authenticate")
