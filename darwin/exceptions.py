from pathlib import Path


class Unauthenticated(Exception):
    """
    Used when a user tries to perform an action that requires authentication without being 
    authenticated.
    """

    pass


class InvalidLogin(Exception):
    """
    Used when a user tries to log in with invalid credentials.
    """

    pass


class InvalidTeam(Exception):
    """
    Used when a team is not found or has no valid API key.
    """

    pass


class MissingConfig(Exception):
    """
    Used when the configuration file was not found.
    """

    pass


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

    pass


class NameTaken(Exception):
    """
    Used when one tries to create an entity and the name of that entity is already taken.
    """

    pass


class ValidationError(Exception):
    """
    Used when a validation fails.
    """

    pass


class Unauthorized(Exception):
    """
    Used when a user tries to perform an action without having the necessary permissions.
    """

    def __str__(self):
        return f"Unauthorized"


class OutdatedDarwinJSONFormat(Exception):
    """
    Used when one tries to parse a video with an old darwin format that is no longer compatible.
    """

    pass

