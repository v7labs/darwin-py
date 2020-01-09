from darwin.exceptions import NameTaken, ValidationError


def name_taken(code, body):
    if code == 422 and body["errors"]["name"][0] == "has already been taken":
        raise NameTaken


def validation_error(code, body):
    if code == 422:
        raise ValidationError(body)
