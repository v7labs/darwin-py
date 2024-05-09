import tempfile
from pathlib import Path
from zipfile import ZipFile

from darwin.dataset.split_manager import split_dataset
from darwin.torch.dataset import InstanceSegmentationDataset


class TestInstanceSegmentationoDatasetLoading:
    def test_split_and_load_instance_segmentation_dataset_images(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with ZipFile("tests/model_training_data.zip") as zfile:
                zfile.extractall(tmpdir)
                dataset_path = (
                    Path(tmpdir) / "model_training_data" / "instance-segmentation-test"
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
                    "random_test": 3,
                    "random_train": 7,
                    "random_val": 2,
                    "stratified_test": 3,
                    "stratified_train": 7,
                    "stratified_val": 2,
                }
                for split_type in split_types:
                    for partition in partitions:
                        dataset_partition = InstanceSegmentationDataset(
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

    def test_split_and_load_instance_segmentation_dataset_videos(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with ZipFile("tests/model_training_data.zip") as zfile:
                zfile.extractall(tmpdir)
                dataset_path = (
                    Path(tmpdir)
                    / "model_training_data"
                    / "instance-segmentation-test-video"
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
                    "random_test": 30,
                    "random_train": 104,
                    "random_val": 15,
                    "stratified_test": 30,
                    "stratified_train": 104,
                    "stratified_val": 15,
                }
                for split_type in split_types:
                    for partition in partitions:
                        dataset_partition = InstanceSegmentationDataset(
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
