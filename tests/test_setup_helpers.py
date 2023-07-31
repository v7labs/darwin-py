import re
from pathlib import Path

import pytest
import responses
from PIL import Image

from e2e_tests.setup_tests import (
    api_call,
    create_dataset,
    create_item,
    create_random_image,
    generate_random_string,
    setup_tests,
    teardown_tests,
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
    assert req_call.request.headers["Authorization"] == "Bearer test_api_key"
    assert req_call.request.body == b'{"key": "json"}'


def test_generate_random_string() -> None:
    for i in range(1, 1000):
        assert len(op := generate_random_string(i)) == i
        assert op.isalnum()


def test_create_dataset() -> None:
    pytest.fail("Not implemented")


def test_create_item() -> None:
    #! TODO: Resume here
    pytest.fail("Not implemented")


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


def test_setup() -> None:
    pytest.fail("Not implemented")


def test_teardown() -> None:
    ...


if __name__ == "__main__":
    pytest.main()
