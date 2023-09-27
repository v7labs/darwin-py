from darwin.future.exceptions.base import DarwinException


class MetaException(DarwinException):
    pass


class MissingSlug(MetaException):
    pass


class MissingDataset(MetaException):
    pass
