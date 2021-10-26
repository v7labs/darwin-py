from darwin.exceptions import NameTaken, ValidationError


def name_taken(code, body) -> None:
    if code != 422:
        return
    if body.get("errors", {}).get("name") == ["has already been taken"]:
        raise NameTaken


def validation_error(code, body) -> None:
    if code == 422:
        raise ValidationError(body)
