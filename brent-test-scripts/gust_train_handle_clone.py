import json
import socket
import time
from datetime import datetime
from pathlib import Path

import darwin
import requests
from darwin.torch.dataset import ObjectDetectionDataset
from darwin.torch.dataset import ClassificationDataset

from darwin.dataset.release import Release

from darwin.dataset.split_manager import split_dataset

# create presigned URL from AWS directly
api_key = "6hYlRDM.0bDPo85RKGbGfHgrIVPeJ3QLUu3c83j7"
dataset_export_s3_url = "https://njord-experiments.s3.eu-west-1.amazonaws.com/exports/3593/lavender/bangladeshi-crops-leaf-disease%40auto-1679417036.zip?response-content-disposition=inline&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEPT%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCWV1LXdlc3QtMyJHMEUCIE1xYHS4tZheVEUyOeBrdPKzK%2BcHPjE30Wk3e2zBfbBuAiEA2kA0jShKTHRGqNVP0bounf1kHhcx%2FA%2Fnq4i8WD4gqboq2QMIvf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAEGgwyNTgzMjc2MTQ4OTIiDBMfCVd4WldTJO8OeCqtA7bvOQez%2BCY8xZAyiWrOm669JT6bQnhBUf1rMYtM9cM6fkCWEhc1Ky2qdcj%2FmIShw%2BKfju1UjDAmj98aZffxKIxAYB9IAagf0fTkSSSGpVAz94bbWSOX%2FB0oSuyudJfle2Gjk7Rcufwuy16g6HZbvHBZHE6fZ3tvOmwSN0GRUbF1JfkMWtFFJ%2F1RS%2F0bBEJ3FWCJWvmnus5wU6Qe9GKcs%2FiSAUZ1un4E5hNRX6W1YxRRKaGHV87DyXQhWn8FgpWoKX%2Bf6qJXTLljOo38VLN9b3hxS6xC9pHQMg7%2BRmdU2rIxlX59%2Bnc91qLlBfIZ9SFJZQxDJuUd2hK9%2FQqkqNeOBa%2Bcd9XE%2BGk8x2MP0TpQdZma34tnhVKMIqCrS8saaZ6giogkipHELUqU78iNfJhWXv3CALeP%2FgGcxeGaf14zjPvexsUrzVRuVmTdzlspiBDbea4vpzB4fW%2BF8ZRBePHoCgJpT0tIbLF3NglZZoUFdXsOVph0YAftnjHOalVw58TofXLKBYfGrVVVWUogv7ClCNrSTIGJ2llgFXOJ31WIWSMDHG0CYDla5nasAcr2pDDoqfCgBjqUAqDs4I2t0lV2clBLF%2BTNl7XOdU3Zv59M%2F6syp0SyaZF9Jncsl2zuArnP9VUoewF%2BtROQPJ0GQbHSDh%2FMcSy%2BCx1nJJtXhOCSjp%2FLeEH3LgJp3xdsCSXZZyOs%2FtbmK3eAQUrAGL%2Bsd3Cyl7jIr%2BsIrScUr0%2BEQ6jY2quqdRxnOpgjDmLJrOnhLh25ujQsrk9%2B5xiXknnhJ4iXila5%2BojFNHHvsfSHgSHs6zIZmXv04kVPswb3mziFlWmecnGgNBeL7NLenpY6HrjMp0AFPgy6K0gEWZWizElBtiS%2BoodiN51IeDn941TA6DpjILVn0ias1HJ7OAWNWxbQNj21Djy9h%2BxLVdfFPUY%2FIKPD1TAh5NaV4j3%2F1Q%3D%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20230323T113755Z&X-Amz-SignedHeaders=host&X-Amz-Expires=43200&X-Amz-Credential=ASIATYJMGSWWHDNSFDOM%2F20230323%2Feu-west-1%2Fs3%2Faws4_request&X-Amz-Signature=38dce0f0c2223433899d21fa88a40127fceef06b1578d267bea62635162a97b8"
dataset_identifier = "lavender/bangladeshi-crops-leaf-disease"

[team_slug, dataset_slug] = dataset_identifier.split("/")



client = darwin.Client.from_api_key(api_key)
dataset = client.get_remote_dataset(dataset_identifier)

# classification v7labs/integration-classification/src/data.py


# object detection

release = Release(
    dataset_slug,
    team_slug,
    version="auto",
    name="auto",
    url=dataset_export_s3_url,
    export_date="now",
    image_count=0,
    class_count=0,
    available=True,
    latest=True,
    format="json",
)
dataset.pull(release=release, video_frames=True)
dataset.split_video_annotations()

dataset_path = dataset.local_path

class_dataset = ClassificationDataset(dataset_path=dataset_path, release_name="latest")


split_path = split_dataset(
            dataset_path,
            release_name="latest",
            val_percentage=0.15,
            test_percentage=0.15 #,
            # stratified_types=["bounding_box"],
        )

split_name = split_path.name


# train_dataset = ObjectDetectionDataset(
#         dataset_path=dataset_path, partition="train", split=split_name, split_type="stratified"
#     )
# val_dataset = ObjectDetectionDataset(
#         dataset_path=dataset_path, partition="val", split=split_name, split_type="stratified"
#     )
# test_dataset = ObjectDetectionDataset(
# dataset_path=dataset_path, partition="test", split=split_name, split_type="stratified"
#     )

# print(f"Train dataset len {len(train_dataset)}")
# print(f"Val dataset len {len(val_dataset)}")
# print(f"Test dataset len {len(test_dataset)}")