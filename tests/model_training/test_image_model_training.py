import tempfile
from pathlib import Path
from zipfile import ZipFile

from darwin.dataset.split_manager import split_dataset
from darwin.torch.dataset import (
    ClassificationDataset,
    InstanceSegmentationDataset,
    ObjectDetectionDataset,
)


class TestImageDatasetLoading:
    def run_split_and_load_image_dataset_test(
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

    def test_split_and_load_classification_dataset_images(self):
        expected_splits = {
            "random_test": 40,
            "random_train": 140,
            "random_val": 20,
            "stratified_test": 40,
            "stratified_train": 140,
            "stratified_val": 20,
        }
        self.run_split_and_load_image_dataset_test(
            "classification-test", ClassificationDataset, expected_splits, "140_20_40"
        )

    def test_split_and_load_instance_segmentation_dataset_images(self):
        expected_splits = {
            "random_test": 3,
            "random_train": 7,
            "random_val": 2,
            "stratified_test": 3,
            "stratified_train": 7,
            "stratified_val": 2,
        }
        self.run_split_and_load_image_dataset_test(
            "instance-segmentation-test",
            InstanceSegmentationDataset,
            expected_splits,
            "7_2_3",
        )

    def test_split_and_load_object_detection_dataset_images(self):
        expected_splits = {
            "random_test": 11,
            "random_train": 37,
            "random_val": 6,
            "stratified_test": 11,
            "stratified_train": 37,
            "stratified_val": 6,
        }
        self.run_split_and_load_image_dataset_test(
            "object-detection-test", ObjectDetectionDataset, expected_splits, "37_6_11"
        )
