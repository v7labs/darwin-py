from __future__ import annotations

from typing import List

from darwin.future.data_objects.item import ItemCreate


async def combined_uploader(
    client,
    team_slug: str,
    dataset_id: int,
    items_to_create: ItemCreate | List[ItemCreate],
    use_folders: bool = False,
    force_slots: bool = False,
):
    ...

    # TODO: Abstraction of the 4-step upload process for meta use
