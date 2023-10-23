from __future__ import annotations

import pprint
from typing import Dict, Generic, Optional, TypeVar

from darwin.future.core.client import ClientCore
from darwin.future.pydantic_base import DefaultDarwin

R = TypeVar("R", bound=DefaultDarwin)
Param = Dict[str, object]


class MetaBase(Generic[R]):
    _element: R
    client: ClientCore

    def __init__(
        self, client: ClientCore, element: R, meta_params: Optional[Param] = None
    ) -> None:
        self.client = client
        self._element = element
        self.meta_params = meta_params or {}

    def __str__(self) -> str:
        class_name = self.__class__.__name__
        if class_name == "Team":
            return f"Team\n\
- Team Name: {self._element.name}\n\
- Team Slug: {self._element.slug}\n\
- Team ID: {self._element.id}\n\
- {len(self._element.members if self._element.members else [])} member(s)"

        elif class_name == "TeamMember":
            return f"Team Member\n\
- Name: {self._element.first_name} {self._element.last_name}\n\
- Role: {self._element.role.value}\n\
- Email: {self._element.email}\n\
- User ID: {self._element.user_id}"

        elif class_name == "Dataset":
            releases = self._element.releases
            return f"Dataset\n\
- Name: {self._element.name}\n\
- Dataset Slug: {self._element.slug}\n\
- Dataset ID: {self._element.id}\n\
- Dataset Releases: {releases if releases else 'No releases'}"

        elif class_name == "Workflow":
            return f"Workflow\n\
- Workflow Name: {self._element.name}\n\
- Workflow ID: {self._element.id}\n\
- Connected Dataset ID: {self._element.dataset.id}\n\
- Conneted Dataset Name: {self._element.dataset.name}"

        elif class_name == "Stage":
            return f"Stage\n\
- Stage Name: {self._element.name}\n\
- Stage Type: {self._element.type.value}\n\
- Stage ID: {self._element.id}"

        else:
            return f"Class type '{class_name}' not found in __str__ method:\
\n{pprint.pformat(self)}"

    def __repr__(self) -> str:
        return str(self._element)
