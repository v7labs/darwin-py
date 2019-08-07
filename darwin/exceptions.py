class Unauthenticated(Exception):
    pass


class InvalidLogin(Exception):
    pass


class MissingConfig(Exception):
    pass


class NotFound(Exception):
    pass


class UnsupportedFileType(Exception):
    def __init__(self, path):
        self.path = path


class InsufficientStorage(Exception):
    pass


class NameTaken(Exception):
    pass


class ValidationError(Exception):
    pass
