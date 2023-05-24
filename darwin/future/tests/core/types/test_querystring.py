from darwin.future.core.types.common import QueryString
from pytest import raises


# happy and sad path tests for QueryString - should validate a dict of strings, and return a query string on str()
def test_querystring_happy_path() -> None:
    query_string = QueryString({"foo": "bar"})
    assert str(query_string) == "?foo=bar"

    query_string_2 = QueryString({"foo": "bar", "baz": "qux"})
    assert str(query_string_2) == "?foo=bar&baz=qux"

    query_string_3 = QueryString(dict())
    assert str(query_string_3) == "?"

    assert query_string.value == {"foo": "bar"}
    assert query_string_2.value == {"foo": "bar", "baz": "qux"}


def test_querystring_sad_path() -> None:
    with raises(AssertionError):
        QueryString({"foo": 1})  # type: ignore
