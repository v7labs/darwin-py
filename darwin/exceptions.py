from cmath import exp
from pathlib import Path
from textwrap import dedent
from typing import List

from jsonschema.exceptions import ValidationError as jscValidationError

from darwin.datatypes import AnnotationFileVersion


class IncompatibleOptions(Exception):
    """
    Used when a combination of options has one or more options that are not compatible between them.
    An option is not compatible with another if any combination from their set of possibilities
    returns an unspecified result.
    """


class UnrecognizableFileEncoding(Exception):
    """
    Used when a we try to decode a file and all decoding algorithms fail.
    """


class Unauthenticated(Exception):
    """
    Used when a user tries to perform an action that requires authentication without being
    authenticated.
    """


class InvalidLogin(Exception):
    """
    Used when a user tries to log in with invalid credentials.
    """


class InvalidTeam(Exception):
    """
    Used when a team is not found or has no valid API key.
    """


class InvalidCompressionLevel(Exception):
    """
    Used when compression level is invalid.
    """

    def __init__(self, level: int):
        """
        Parameters
        ----------
        level: int
            The new value of compression level.
        """
        super().__init__()
        self.level = level

    def __str__(self):
        return f"Unsupported compression level: '{self.level}'. Supported compression levels are 0-9."


class MissingConfig(Exception):
    """
    Used when the configuration file was not found.
    """


class UnsupportedExportFormat(Exception):
    """
    Used when one tries to export an annotation into a format that is not supported.
    """

    def __init__(self, format: str):
        """
        Parameters
        ----------
        format: str
            The unsupported format.
        """
        super().__init__()
        self.format = format


class NotFound(Exception):
    """Used when a given resource is not found."""

    def __init__(self, name: str):
        """
        Parameters
        ----------
        name: str
            The name of the resource.
        """
        super().__init__()
        self.name = name

    def __str__(self):
        return f"Not found: '{self.name}'"


class UnsupportedFileType(Exception):
    """
    Used when a given does not have a supported video or image extension.
    """

    def __init__(self, path: Path):
        """
        Parameters
        ----------
        path: Path
            The path of the file.
        """
        self.path = path


class InsufficientStorage(Exception):
    """
    Used when a request to a server fails due to insufficient storage.
    """


class NameTaken(Exception):
    """
    Used when one tries to create an entity and the name of that entity is already taken.
    """


class ValidationError(Exception):
    """
    Used when a validation fails.
    """


class Unauthorized(Exception):
    """
    Used when a user tries to perform an action without having the necessary permissions.
    """

    def __str__(self):
        return "Unauthorized"


class OutdatedDarwinJSONFormat(Exception):
    """
    Used when one tries to parse a video with an old darwin format that is no longer compatible.
    """


class RequestEntitySizeExceeded(Exception):
    """
    Used when a request fails due to the URL being too long.
    """


class MissingSchema(Exception):
    """
    Used to indicate a problem loading or finding the schema
    """

    def __init__(self, message: str):
        """_summary_

        Parameters
        ----------
        message : str
            Message to propogate up the stack
        """
        self.message = message

    def __str__(self) -> str:
        return self.message


class AnnotationFileValidationError(Exception):
    """
    Used to indicate error while validation JSON annotation files.
    """

    def __init__(self, parent_error: jscValidationError, file_path: Path):
        """
        Parameters
        ----------
        parent_error: ValidationError
            Error reported by ``jsonschema``.
        file_path: Path
            Path to annotation file that failed to validate.
        """
        self.parent_error = parent_error
        self.file_path = file_path

    def __str__(self) -> str:
        return f"Unable to verify annotation file: '{self.file_path}'\n\n{self.parent_error.__str__()}".rstrip()


class UnknownAnnotationFileSchema(Exception):
    """
    Used to indicate error when inferring schema for JSON annotation file.
    """

    def __init__(
        self, file_path: Path, supported_versions: List[AnnotationFileVersion], detected_version: AnnotationFileVersion
    ):
        """
        Parameters
        ----------
        file_path: Path
            Path to annotation file that failed to validate.

        supported_versions: List[AnnotationFileVersion]
            todo

        detected_version: AnnotationFileVersion
            todo
        """
        self.file_path = file_path
        self.detected_version = detected_version
        self.supported_versions = list(map(str, supported_versions))

    def __str__(self) -> str:
        return dedent(
            f"""\
            Unable to find JSON schema for annotation file: '{self.file_path}'

            Given annotation file should have either:
                * optional `schema_ref` field with URL to JSON schema
                * `version` field set to one of supported natively versions: {self.supported_versions}

            Detected annotation file version is: '{self.detected_version}'.
            """
        )


class UnknownExportVersion(Exception):
    """Used when dataset version is not recognized."""

    def __init__(self, version: str):
        """
        Parameters
        ----------
        version: str
            The version that is not recognized.
        """
        super().__init__()
        self.version = version

    def __str__(self):
        return f"Unknown version: '{self.version}'"


class UnsupportedImportAnnotationType(Exception):
    """
    Used when one tries to parse an annotation with an unsupported type.
    """

    def __init__(self, import_type: str, annotation_type: str):
        """
        Parameters
        ----------
        import_type: str
            The type of import, e.g. "dataloop".
        annotation_type: str
            The unsupported annotation type.
        """
        super().__init__(f"Unsupported annotation type {annotation_type} for {import_type} import")
        self.import_type = import_type
        self.annotation_type = annotation_type


class DataloopComplexPolygonsNotYetSupported(Exception):
    """
    Used when one tries to parse an annotation with a complex polygon.
    """

    def __init__(
        self,
    ):
        """
        Parameters
        ----------
        import_type: str
            The type of import, e.g. "dataloop".
        annotation_type: str
            The unsupported annotation type.
        """
        super().__init__("Complex polygons not yet supported for dataloop import")
