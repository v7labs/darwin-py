from subprocess import run
from time import sleep
from typing import Optional, Union, Sequence

from attr import dataclass
from darwin.exceptions import DarwinException
import datetime
import json
import re
import uuid
import pytest
import requests
import time
from e2e_tests.objects import E2EDataset, ConfigValues
from darwin.dataset.release import Release, ReleaseStatus
import darwin.datatypes as dt


@dataclass
class CLIResult:
    """Wrapper for the result of a CLI command after decoding the stdout and stderr."""

    return_code: int
    stdout: str
    stderr: str


SERVER_WAIT_TIME = 10


@pytest.fixture
def new_dataset() -> E2EDataset:
    """Create a new dataset via darwin cli and return the dataset object, complete with teardown"""
    uuid_str = str(uuid.uuid4())
    new_dataset_name = "test_dataset_" + uuid_str
    result = run_cli_command(f"darwin dataset create {new_dataset_name}")
    assert_cli(result, 0)
    id_raw = re.findall(r"datasets[/\\+](\d+)", result.stdout)
    assert id_raw is not None and len(id_raw) == 1
    id = int(id_raw[0])
    teardown_dataset = E2EDataset(id, new_dataset_name, None)
    pytest.datasets.append(teardown_dataset)  # type: ignore
    return teardown_dataset


def run_cli_command(
    command: str,
    working_directory: Optional[str] = None,
    yes: bool = False,
    server_wait: int = SERVER_WAIT_TIME,
) -> CLIResult:
    """
    Run a CLI command and return the return code, stdout, and stderr.

    Parameters
    ----------
    command : str
        The command to run.
    working_directory : str, optional
        The working directory to run the command in.

    Returns
    -------
    Tuple[int, str, str]
        The return code, stdout, and stderr.
    """

    # Do not allow directory traversal
    if ".." in command or (working_directory and ".." in working_directory):
        raise DarwinException("Cannot pass directory traversal to 'run_cli_command'.")

    if yes:
        command = f"yes Y | {command}"

    # Prefix the command with 'poetry run' to ensure it runs in the Poetry shell
    command = f"poetry run {command}"

    if working_directory:
        result = run(
            command,
            cwd=working_directory,
            capture_output=True,
            shell=True,
        )
    else:
        result = run(
            command,
            capture_output=True,
            shell=True,
        )
    sleep(server_wait)  # wait for server to catch up
    try:
        return CLIResult(
            result.returncode,
            result.stdout.decode("utf-8"),
            result.stderr.decode("utf-8"),
        )
    except UnicodeDecodeError:
        return CLIResult(
            result.returncode,
            result.stdout.decode("cp437"),
            result.stderr.decode("cp437"),
        )


def format_cli_output(result: CLIResult) -> str:
    return f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}\n"


def assert_cli(
    result: CLIResult,
    expected_return_code: int = 0,
    in_stdout: Optional[str] = None,
    in_stderr: Optional[str] = None,
    expected_stdout: Optional[str] = None,
    expected_stderr: Optional[str] = None,
    inverse: bool = False,
) -> None:
    assert result.return_code == expected_return_code, format_cli_output(result)
    if not inverse:
        if in_stdout:
            assert in_stdout in result.stdout, format_cli_output(result)
        if in_stderr:
            assert in_stderr in result.stderr, format_cli_output(result)
        if expected_stdout:
            assert result.stdout == expected_stdout, format_cli_output(result)
        if expected_stderr:
            assert result.stderr == expected_stderr, format_cli_output(result)
    else:
        if in_stdout:
            assert in_stdout not in result.stdout, format_cli_output(result)
        if in_stderr:
            assert in_stderr not in result.stderr, format_cli_output(result)
        if expected_stdout:
            assert result.stdout != expected_stdout, format_cli_output(result)
        if expected_stderr:
            assert result.stderr != expected_stderr, format_cli_output(result)


def list_items(api_key, dataset_id, team_slug, base_url):
    """
    List items in Darwin dataset, handling pagination.
    """
    url = f"{base_url}/api/v2/teams/{team_slug}/items?dataset_ids={dataset_id}"
    headers = {"accept": "application/json", "Authorization": f"ApiKey {api_key}"}
    items = []

    while url:
        response = requests.get(url, headers=headers)
        if response.ok:
            data = json.loads(response.text)
            items.extend(data["items"])
            next_page = data.get("page", {}).get("next")
            if next_page:
                url = f"{base_url}/{team_slug}/items?dataset_ids={dataset_id}&page[from]={next_page}"
            else:
                url = None
        else:
            raise requests.exceptions.HTTPError(
                f"GET request failed with status code {response.status_code}."
            )

    return items


def wait_until_items_processed(
    config_values: ConfigValues, dataset_id: int, timeout: int = 600
):
    """
    Waits until all items in a dataset have finished processing before attempting to upload annotations.
    Raises a `TimeoutError` if the process takes longer than the specified timeout.
    """
    sleep_duration = SERVER_WAIT_TIME
    api_key = config_values.api_key
    team_slug = config_values.team_slug
    base_url = config_values.server
    elapsed_time = 0

    while elapsed_time < timeout:
        items = list_items(api_key, dataset_id, team_slug, base_url)
        if not items:
            return
        if all(item["processing_status"] == "complete" for item in items):
            break
        print(f"Waiting {sleep_duration} seconds for items to finish processing...")
        time.sleep(sleep_duration)
        elapsed_time += sleep_duration

    if elapsed_time >= timeout:
        raise TimeoutError(
            f"Processing items took longer than the specified timeout of {timeout} seconds."
        )


def export_release(
    annotation_format: str,
    local_dataset: E2EDataset,
    config_values: ConfigValues,
    release_name: Optional[str] = "all-files",
) -> Release:
    """
    Creates an export of all items in the given dataset.
    Waits for the export to finish, then downloads and the annotation files to
    `actual_annotations_dir`
    """
    dataset_slug = local_dataset.slug
    team_slug = config_values.team_slug
    api_key = config_values.api_key
    base_url = config_values.server
    create_export_url = (
        f"{base_url}/api/v2/teams/{team_slug}/datasets/{dataset_slug}/exports"
    )

    # Necessary because these are the only formats where `annotation_format` does not match the required payload value
    if annotation_format == "darwin":
        annotation_format = "darwin_json_2"
    elif annotation_format == "pascal_voc":
        annotation_format = "pascalvoc"
    payload = {
        "filters": {"statuses": ["new", "annotate", "review", "complete"]},
        "include_authorship": False,
        "include_export_token": False,
        "format": f"{annotation_format}",
        "name": f"{release_name}",
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"ApiKey {api_key}",
    }
    response = requests.post(create_export_url, json=payload, headers=headers)
    list_export_url = (
        f"{base_url}/api/v2/teams/{team_slug}/datasets/{dataset_slug}/exports"
    )
    ready = False
    while not ready:
        sleep(5)
        print("Trying to get release...")
        response = requests.get(list_export_url, headers=headers)
        exports = response.json()
        for export in exports:
            if export["name"] == release_name and export["status"] == "complete":
                export_data = export
                ready = True

    release = Release(
        dataset_slug=dataset_slug,
        team_slug=team_slug,
        version=export_data["version"],
        name=export_data["name"],
        status=ReleaseStatus.COMPLETE,
        url=export_data["download_url"],
        export_date=datetime.datetime.strptime(
            export_data["inserted_at"], "%Y-%m-%dT%H:%M:%SZ"
        ),
        image_count=export_data["metadata"]["num_images"],
        class_count=len(export_data["metadata"]["annotation_classes"]),
        available=True,
        latest=export_data["latest"],
        format=export_data.get("format", "json"),
    )
    return release


def delete_annotation_uuids(
    annotations: Sequence[Union[dt.Annotation, dt.VideoAnnotation]],
):
    """
    Removes all UUIDs present in instances of `dt.Annotation` and `dt.VideoAnnotation` objects.

    This allows for equality to be asserted with other annotations.
    """
    for annotation in annotations:
        if isinstance(annotation, dt.Annotation):
            del annotation.id
            if annotation.annotation_class.annotation_type == "raster_layer":
                del annotation.data["mask_annotation_ids_mapping"]
        elif isinstance(annotation, dt.VideoAnnotation):
            del annotation.id
            for frame in annotation.frames.keys():
                del annotation.frames[frame].id
                if annotation.annotation_class.annotation_type == "raster_layer":
                    del annotation.frames[frame].data["mask_annotation_ids_mapping"]


def exclude_annotations_of_type(
    annotation_type: str,
    annotations: Sequence[Union[dt.Annotation, dt.VideoAnnotation]],
) -> Sequence[Union[dt.Annotation, dt.VideoAnnotation]]:
    """
    Filters out all annotation objects of given type.
    """
    return [
        annotation
        for annotation in annotations
        if annotation.annotation_class.annotation_type != annotation_type
    ]
