from enum import Enum


class DocEnum(Enum):
    """
    Documenting Enums in Python is not supported by many tools. Therefore this class was created to
    support just that. It is basically a hack to allow Enum documentation.
    `See more here <https://stackoverflow.com/a/50473952/1337392>`
    """

    def __new__(cls, value, doc=None):
        self = object.__new__(cls)  # calling super().__new__(value) here would fail
        self._value_ = value
        if doc is not None:
            self.__doc__ = doc
        return self
