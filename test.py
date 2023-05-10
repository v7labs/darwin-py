from pathlib import Path

from darwin.dataset.local_dataset import LocalDataset

path = Path("/Users/nathanperkins/.darwin/datasets/v7-labs/io-1072/")
test = LocalDataset(path, "polygon")
