import pytest

from darwin.future.data_objects.page import Page


def test_default_page() -> None:
    page = Page.default()
    assert page.offset == 0
    assert page.size == 500
    assert page.count == 0


def test_to_query_string() -> None:
    page = Page(offset=0, size=10, count=100)
    qs = page.to_query_string()
    assert qs.value == {"page[offset]": "0", "page[size]": "10"}


def test_increment() -> None:
    page = Page(offset=0, size=10, count=100)
    page.increment()
    assert page.offset == 10
    assert page.size == 10


@pytest.mark.parametrize(
    "size, index, expected_offset", [(10, 0, 0), (10, 9, 0), (10, 10, 1)]
)
def test_get_required_page(size: int, index: int, expected_offset: int) -> None:
    page = Page(size=size)
    required_page = page.get_required_page(index)
    assert required_page.offset == expected_offset
    assert required_page.size == size
