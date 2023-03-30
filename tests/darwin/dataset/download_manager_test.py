from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import responses

from darwin.client import Client
from darwin.config import Config
from darwin.dataset import RemoteDataset
from darwin.dataset import download_manager as dm
from darwin.dataset.identifier import DatasetIdentifier
from darwin.dataset.remote_dataset_v1 import RemoteDatasetV1
from tests.fixtures import *
