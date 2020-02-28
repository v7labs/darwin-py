from typing import Callable

from darwin.exceptions import NameTaken, ValidationError

ErrorHandlerType = Callable[[int, dict], None]


def name_taken(code: int, body: dict):
    if code == 422 and body["errors"]["name"][0] == "has already been taken":
        raise NameTaken


def validation_error(code: int, body: dict):
    if code == 422:
        raise ValidationError(body)
