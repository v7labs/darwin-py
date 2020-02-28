from pathlib import Path

from darwin.client import Client
from darwin.config import Config

res_path = Path("tests") / "res"


def setup_client():
    config = Config(res_path / "config.yaml")
    return Client(config)
