from darwin.exceptions import NameTaken, ValidationError


def name_taken(code, body):
    if code != 422:
        return

    if "errors" not in body:
        return

    errors = body["errors"]
    if errors.get("name") == ["has already been taken"]:
        raise NameTaken

    metadata = errors.get("metadata")
    if metadata is None:
        return

    if len(metadata) > 0 and metadata[0] == "has already been taken":
        raise NameTaken


def validation_error(code, body):
    if code == 422:
        raise ValidationError(body)
