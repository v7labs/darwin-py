from __future__ import annotations

from typing import Dict, Generic, Optional, TypeVar

from darwin.future.core.client import ClientCore

R = TypeVar("R")
Param = Dict[str, object]


class MetaBase(Generic[R]):
    """
    A base class for metadata objects. This should only ever be inherited from in meta objects.
    stores metadata parameters used to access the api that are related to the Meta Objects
    but potentially not required for the core object. For example, a dataset object needs
    the team slug to access the api which get's passed down from the team object.

    Attributes:
        _element (R): The element R to which the object is related.
        client (ClientCore): The client used to execute the query.
        meta_params (Dict[str, object]): A dictionary of metadata parameters. This is
            used in conjuction with the Query object to execute related api calls.

    Methods:
        __init__(client: ClientCore, element: R, meta_params: Optional[Param] = None) -> None:
            Initializes a new MetaBase object.
        __repr__() -> str:
            Returns a string representation of the object.

    Examples:
        # Create a MetaBase type that manages a TeamCore object from the API
        class Team(MetaBase[TeamCore]):
            ...
    """

    _element: R
    client: ClientCore

    def __init__(
        self,
        element: R,
        client: ClientCore,
        meta_params: Optional[Param] = None,
    ) -> None:
        self.client = client
        self._element = element
        self.meta_params = meta_params or {}

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self._element})"
