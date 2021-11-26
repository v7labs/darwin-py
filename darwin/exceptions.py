from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


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


class UploadStage(Enum):
    REQUEST_SIGNATURE = 0
    UPLOAD_TO_S3 = 1
    CONFIRM_UPLOAD_COMPLETE = 2
    OTHER = 3


@dataclass
class UploadRequestError(Exception):
    file_path: Path
    stage: UploadStage
    error: Optional[Exception] = None
