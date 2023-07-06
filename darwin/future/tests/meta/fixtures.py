from pytest import fixture, raises

from darwin.future.core.client import DarwinConfig
from darwin.future.meta.client import MetaClient
from darwin.future.tests.core.fixtures import *


@fixture
def base_meta_client(base_config: DarwinConfig) -> MetaClient:
    return MetaClient(base_config)