from typing import List

from attrs import define, field
from attrs.validators import instance_of

from darwin.future.data_objects.attr_utils import lowercase


@define
class Release:
    name: str = field(validator=instance_of(str), default="latest", converter=lowercase)


@define
class Dataset:
    name: str = field(validator=instance_of(str), converter=lowercase)
    releases: List[Release] = []


@define
class Team:
    name: str
    datasets: List[Dataset] = []
