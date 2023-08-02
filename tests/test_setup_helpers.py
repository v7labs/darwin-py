import re
from pathlib import Path
from unittest.mock import patch

import pytest
import responses
from PIL import Image

from e2e_tests.conftest import ConfigValues
from e2e_tests.setup_tests import (
    api_call,
    create_dataset,
    create_item,
    create_random_image,
    generate_random_string,
)


@responses.activate
def test_api_call() -> None:
    responses.add(
        responses.GET,
        "http://0.0.0.0/testurl",
        status=218,
    )

    api_call("get", "http://0.0.0.0/testurl", {"key": "json"}, "test_api_key")

    assert len(responses.calls) == 1
    req_call: responses.Call = responses.calls[0]  # type: ignore

    assert req_call.request.url == "http://0.0.0.0/testurl"
    assert req_call.request.headers["Authorization"] == "ApiKey test_api_key"
    assert req_call.request.body == b'{"key": "json"}'  # type: ignore


def test_generate_random_string() -> None:
    for i in range(1, 1000):
        assert len(op := generate_random_string(i)) == i
        assert op.isalnum()


def test_create_dataset() -> None:
    with patch("e2e_tests.setup_tests.api_call") as mock_api_call:
        mock_api_call.return_value.ok = True
        mock_api_call.return_value.status_code = 200
        mock_api_call.return_value.text = "test_text"
        mock_api_call.return_value.json.return_value = {
            "active": True,
            "annotation_hotkeys": {},
            "annotators_can_create_tags": True,
            "annotators_can_instantiate_workflows": True,
            "anyone_can_double_assign": False,
            "archived": False,
            "archived_at": None,
            "default_workflow_template_id": 1337,
            "id": 13371337,
            "instructions": "",
            "name": "test_dataset",
            "num_classes": 0,
            "num_images": 0,
            "owner_id": 101,
            "parent_id": None,
            "pdf_fit_page": True,
            "progress": 0.0,
            "public": None,
            "reviewers_can_annotate": False,
            "slug": "test_dataset",
            "team_id": 123,
            "team_slug": "test-team",
            "thumbnails": [],
            "version": 1,
            "work_prioritization": "inserted_at:desc",
            "work_size": 30,
            "workflow_ids": [],
        }

        dataset = create_dataset(
            "test-prefix", ConfigValues(api_key="test_api_key", server="https://test_server", team_slug="test_team")
        )

    if not dataset:
        pytest.fail("Dataset was not created")
    else:
        assert dataset.name == "test_dataset"
        assert dataset.id == 13371337
        assert dataset.slug == "test_dataset"


def test_create_item(tmpdir: Path) -> None:
    with patch("e2e_tests.setup_tests.api_call") as mock_api_call:
        mock_api_call.return_value.ok = True
        mock_api_call.return_value.status_code = 200
        mock_api_call.return_value.text = "test_text"
        mock_api_call.return_value.json.return_value = {
            # fmt: off
            "items": [
                {
                    "id": "test_id", 
                    "name": "test_dataset",
                    "path": "test_path",
                    "slots": [
                        {
                            "file_name": "slot_file_name",
                            "slot_name": "slot_name",
                        }
                    ],
                }
            ]
            # fmt: on
        }

        image_path = create_random_image("test_prefix", Path(tmpdir))

        item = create_item(
            # fmt: off
            "test_dataset", 
            "test_prefix", 
            image_path, 
            ConfigValues(api_key="test_api_key", server="test_server", team_slug="test_team")
            # fmt: on
        )

    if not item:
        pytest.fail("Item was not created")
    else:
        assert item.name == "test_dataset"
        assert item.path == "test_path"
        assert item.id == "test_id"
        assert item.file_name == "slot_file_name"
        assert item.slot_name == "slot_name"


def test_create_random_image(tmpdir: Path) -> None:
    image_location = create_random_image("prefix", Path(tmpdir))
    assert image_location.exists()
    assert image_location.is_file()
    FILENAME_MATCHER = re.compile(r"^prefix\_[A-z0-9]+\.png$")
    assert FILENAME_MATCHER.match(image_location.name)
    assert Image.open(image_location).size == (10, 10)

    image_2 = create_random_image("prefix", Path(tmpdir), 5, 9)
    assert image_2.exists()
    assert Image.open(image_2).size == (9, 5)


@pytest.mark.xfail("Not implemented")
def test_setup() -> None:
    pytest.fail("Not implemented")


@pytest.mark.xfail("Not implemented")
def test_teardown() -> None:
    pytest.fail("Not implemented")


if __name__ == "__main__":
    pytest.main()
