from typing import Type


def assert_is(
    conditional: bool,
    message: str,
    exception_factory: Type[BaseException] = AssertionError,
) -> None:
    if not conditional:
        raise exception_factory(message)
