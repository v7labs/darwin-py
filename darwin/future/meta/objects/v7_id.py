from uuid import UUID

from darwin.future.meta.objects.base import MetaBase


class V7ID(MetaBase[UUID]):
    @property
    def id(self) -> UUID:
        return self._element

    def __str__(self) -> str:
        return str(self._element)

    def __repr__(self) -> str:
        return str(self)
