from darwin.future.core.types.common import QueryString


# happy and sad path tests for QueryString
# should validate a dict of strings, and return a query string on str()
def test_querystring_happy_path() -> None:
    query_string = QueryString({"foo": "bar"})
    assert str(query_string) == "?foo=bar"

    query_string_2 = QueryString({"foo": "bar", "baz": "qux"})
    assert str(query_string_2) == "?foo=bar&baz=qux"

    query_string_3 = QueryString({})
    assert str(query_string_3) == ""

    assert query_string.value == {"foo": "bar"}
    assert query_string_2.value == {"foo": "bar", "baz": "qux"}


def test_querystring_coerces_list() -> None:
    query_string = QueryString({"foo": ["bar", "baz"]})
    assert str(query_string) == "?foo=bar&foo=baz"
    assert query_string.value == {"foo": ["bar", "baz"]}


def test_querystring_coerces_stringable() -> None:
    class Stringable:
        def __str__(self) -> str:
            return "bar"

    query_string = QueryString({"foo": Stringable()})
    assert str(query_string) == "?foo=bar"
    assert query_string.value == {"foo": "bar"}
