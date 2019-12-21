class Unauthenticated(Exception):
    pass


class InvalidLogin(Exception):
    pass


class InvalidTeam(Exception):
    pass


class MissingConfig(Exception):
    pass


class NotFound(Exception):
    def __init__(self, name):
        super().__init__()
        self.name = name


class UnsupportedFileType(Exception):
    def __init__(self, path):
        self.path = path


class InsufficientStorage(Exception):
    pass


class NameTaken(Exception):
    pass


class ValidationError(Exception):
    pass


class Unauthorized(Exception):
    pass


#TODO not sure if this is the best place, but we need them in some kind of "shared" location (e.g. utils-like)
def name_taken(code, body):
    if code == 422 and body["errors"]["name"][0] == "has already been taken":
        raise NameTaken


def validation_error(code, body):
    if code == 422:
        raise ValidationError(body)