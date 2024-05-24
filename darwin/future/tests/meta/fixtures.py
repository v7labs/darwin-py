from pytest import fixture

from darwin.future.core.client import DarwinConfig
from darwin.future.meta.client import Client
from darwin.future.tests.core.fixtures import *


@fixture
def base_meta_client(base_config: DarwinConfig) -> Client:
    return Client(base_config)
