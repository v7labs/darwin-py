import json
import socket
import time
from datetime import datetime

import requests
from darwin import Client
from darwin.dataset.release import Release

UPLOAD_RETRY_SECONDS = 10


def upload(url, data, files, retry=False, raise_on_error=False):
    attempts = 5 if retry else 1
    for attempt in range(attempts, -1, -1):
        try:
            return requests.post(url, data=data, files=files)
        except requests.exceptions.ConnectionError as e:
            print(f"Connection Error, Retrying in {UPLOAD_RETRY_SECONDS} seconds...")
            time.sleep(UPLOAD_RETRY_SECONDS)
            if raise_on_error and attempt == 0:
                raise e
        except Exception as e:
            print("Upload exception:", e)
            print(f"Retrying in {UPLOAD_RETRY_SECONDS} seconds...")
            time.sleep(UPLOAD_RETRY_SECONDS)
            if raise_on_error and attempt == 0:
                raise e


class TrainHandler:
    def __init__(self, action):
        self.action = action

        self.chunk_byte_size = 256 * 1024
        self.dataset_path = None
        self.log = ""
        self.metrics = {}

        self._connect_to_metrics_socket()

    def send(self, message):
        message["request_id"] = self.action.request_id
        binary_message = json.dumps(message).encode("utf-8")
        binary_message = str(len(binary_message)).encode("utf-8") + b";" + binary_message
        self.metrics_socket.sendall(binary_message)

    def log_metric(self, name, value, x=None):
        if x is None:
            if name in self.metrics:
                self.metrics[name] += 1
            else:
                self.metrics[name] = 1
            x = self.metrics[name]

        message = {"command": "log_metric", "name": name, "value": value, "x": x}

        self.send(message)

    def register_training_stats(self, training_stats):
        message = {"command": "register_training_stats", "training_stats": training_stats}

        self.send(message)

    def download_dataset(self):
        api_key = self.action.payload["api_key"]
        dataset_export_s3_url = self.action.payload["dataset_export_s3_url"]
        dataset_identifier = self.action.payload["dataset_identifier"]
        [team_slug, dataset_slug] = dataset_identifier.split("/")

        client = Client.from_api_key(api_key)
        dataset = client.get_remote_dataset(dataset_identifier)
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

        self.dataset_path = dataset.local_path

    def maybe_request_log_upload(self):
        log_bytes = self.log.encode("utf-8")
        if len(log_bytes) > self.chunk_byte_size:
            self.upload_log()

    def set_tracked(self, name, value):
        self.log += f"!{name},{value}\n"
        self.maybe_request_log_upload()

    def write_log(self, entry):
        print(entry)
        self.log += f"{entry}\n"
        self.maybe_request_log_upload()

    def upload_checkpoint(self, path):
        with open(path, "rb") as f:
            url = f"http:{self.action.payload['presigned_checkpoint_url']['postEndpoint']}"
            data = self.action.payload["presigned_checkpoint_url"]["signature"]
            files = {"file": (path, f)}
            return upload(url, data, files, retry=True, raise_on_error=True)

    def upload_log(self):
        log_path = f"{datetime.now()}.log"
        # Write log to a file
        with open(log_path, "w") as f:
            f.write(self.log)
        # Upload file to S3
        with open(log_path, "rb") as f:
            url = f"http:{self.action.payload['presigned_log_url']['postEndpoint']}"
            data = self.action.payload["presigned_log_url"]["signature"]
            files = {"file": (log_path, f)}
            return upload(url, data, files)

    def _connect_to_metrics_socket(self):
        self.metrics_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.metrics_socket.connect("/tmp/metrics.sock")
