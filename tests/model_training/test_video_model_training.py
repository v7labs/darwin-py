import tempfile
from pathlib import Path
from zipfile import ZipFile

from darwin.dataset.split_manager import split_dataset
from darwin.torch.dataset import (
    ClassificationDataset,
    InstanceSegmentationDataset,
    ObjectDetectionDataset,
)


class TestVideoDatasetLoading:
    def run_split_and_load_video_dataset_test(
        self, dataset_name, dataset_class, expected_splits, split_values
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            with ZipFile("tests/model_training_data.zip") as zfile:
                zfile.extractall(tmpdir)
                dataset_path = Path(tmpdir) / "model_training_data" / dataset_name

                split_dataset(
                    dataset_path=dataset_path,
                    release_name="complete",
                    val_percentage=0.1,
                    test_percentage=0.2,
                )

                split_types = ["random", "stratified"]
                partitions = ["test", "train", "val"]
                for split_type in split_types:
                    for partition in partitions:
                        dataset_partition = dataset_class(
                            dataset_path=dataset_path,
                            release_name="complete",
                            partition=partition,
                            split_type=split_type,
                            split=split_values,
                        )
                        assert (
                            len(dataset_partition.annotations_path)
                            == expected_splits[f"{split_type}_{partition}"]
                        )
                        assert (
                            len(dataset_partition.images_path)
                            == expected_splits[f"{split_type}_{partition}"]
                        )

    def test_split_and_load_classification_dataset_video(self):
        expected_splits = {
            "random_test": 60,
            "random_train": 210,
            "random_val": 30,
            "stratified_test": 60,
            "stratified_train": 210,
            "stratified_val": 30,
        }
        self.run_split_and_load_video_dataset_test(
            "classification-test-video",
            ClassificationDataset,
            expected_splits,
            "210_30_60",
        )

    def test_split_and_load_instance_segmentation_dataset_video(self):
        expected_splits = {
            "random_test": 30,
            "random_train": 105,
            "random_val": 15,
            "stratified_test": 30,
            "stratified_train": 105,
            "stratified_val": 15,
        }
        self.run_split_and_load_video_dataset_test(
            "instance-segmentation-test-video",
            InstanceSegmentationDataset,
            expected_splits,
            "105_15_30",
        )

    def test_split_and_load_object_detection_dataset_video(self):
        expected_splits = {
            "random_test": 30,
            "random_train": 105,
            "random_val": 15,
            "stratified_test": 30,
            "stratified_train": 105,
            "stratified_val": 15,
        }
        self.run_split_and_load_video_dataset_test(
            "object-detection-test-video",
            ObjectDetectionDataset,
            expected_splits,
            "105_15_30",
        )
