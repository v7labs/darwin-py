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


class OutdatedDarwinJSONFormat(Exception):
    pass
