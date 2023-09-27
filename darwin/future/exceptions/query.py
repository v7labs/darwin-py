from darwin.future.exceptions.base import DarwinException


class ResultsNotFound(DarwinException):
    pass


class MoreThanOneResultFound(DarwinException):
    pass


class InvalidQueryModifier(DarwinException):
    pass


class InvalidQueryFilter(DarwinException):
    pass
