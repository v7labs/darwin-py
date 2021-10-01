class Unauthenticated(Exception):
    pass


class InvalidLogin(Exception):
    pass


class InvalidTeam(Exception):
    pass


class MissingConfig(Exception):
    pass


class UnsupportedExportFormat(Exception):
    def __init__(self, format):
        super().__init__()
        self.format = format


class NotFound(Exception):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def __str__(self):
        return f"Not found: '{self.name}'"


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
    def __str__(self):
        return f"Unauthorized"


class OutdatedDarwinJSONFormat(Exception):
    pass
