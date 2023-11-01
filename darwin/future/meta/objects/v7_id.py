from uuid import UUID

from darwin.future.meta.objects.base import MetaBase


class V7ID(MetaBase[UUID]):
    def __str__(self) -> str:
        return str(self._element)

    def __repr__(self) -> str:
        return str(self)
