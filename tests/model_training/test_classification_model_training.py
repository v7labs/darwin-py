import tempfile
from pathlib import Path
from zipfile import ZipFile

from darwin.dataset.split_manager import split_dataset
from darwin.torch.dataset import ClassificationDataset


class TestClassificationDatasetLoading:
    def test_split_and_load_classification_dataset_images(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with ZipFile("tests/model_training_data.zip") as zfile:
                zfile.extractall(tmpdir)
                dataset_path = (
                    Path(tmpdir) / "model_training_data" / "classification-test"
                )
                split_dataset(
                    dataset_path=dataset_path,
                    release_name="complete",
                    val_percentage=0.1,
                    test_percentage=0.2,
                )

                split_types = ["random", "stratified"]
                partitions = ["test", "train", "val"]
                expected_splits = {
                    "random_test": 40,
                    "random_train": 140,
                    "random_val": 20,
                    "stratified_test": 40,
                    "stratified_train": 140,
                    "stratified_val": 20,
                }
                for split_type in split_types:
                    for partition in partitions:
                        dataset_partition = ClassificationDataset(
                            dataset_path=dataset_path,
                            release_name="complete",
                            partition=partition,
                            split_type=split_type,
                        )
                        assert (
                            len(dataset_partition.annotations_path)
                            == expected_splits[f"{split_type}_{partition}"]
                        )
                        assert (
                            len(dataset_partition.images_path)
                            == expected_splits[f"{split_type}_{partition}"]
                        )

    def test_split_and_load_classification_dataset_videos(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with ZipFile("tests/model_training_data.zip") as zfile:
                zfile.extractall(tmpdir)
                dataset_path = (
                    Path(tmpdir) / "model_training_data" / "classification-test-video"
                )
                split_dataset(
                    dataset_path=dataset_path,
                    release_name="complete",
                    val_percentage=0.1,
                    test_percentage=0.2,
                )

                split_types = ["random", "stratified"]
                partitions = ["test", "train", "val"]
                expected_splits = {
                    "random_test": 60,
                    "random_train": 210,
                    "random_val": 30,
                    "stratified_test": 60,
                    "stratified_train": 210,
                    "stratified_val": 30,
                }
                for split_type in split_types:
                    for partition in partitions:
                        dataset_partition = ClassificationDataset(
                            dataset_path=dataset_path,
                            release_name="complete",
                            partition=partition,
                            split_type=split_type,
                        )
                        assert (
                            len(dataset_partition.annotations_path)
                            == expected_splits[f"{split_type}_{partition}"]
                        )
                        assert (
                            len(dataset_partition.images_path)
                            == expected_splits[f"{split_type}_{partition}"]
                        )
