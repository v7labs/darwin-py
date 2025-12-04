"""
Storage uploader module for uploading video artifacts to external cloud storage.

Supports AWS S3, Google Cloud Storage, and Azure Blob Storage with exponential
backoff retry logic for transient failures.
"""

import os
import random
import socket
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Set

from darwin.datatypes import ObjectStore

# Retryable HTTP status codes:
# - 408: Request Timeout
# - 429: Too Many Requests (rate limiting)
# - 500: Internal Server Error
# - 502: Bad Gateway
# - 503: Service Unavailable
# - 504: Gateway Timeout
RETRYABLE_STATUS_CODES: Set[int] = {408, 429, 500, 502, 503, 504}


class StorageClient(ABC):
    """Abstract base class for cloud storage clients."""

    @abstractmethod
    def upload_file(self, local_path: str, storage_key: str) -> None:
        """
        Upload a file to cloud storage.

        Parameters
        ----------
        local_path : str
            Path to local file to upload
        storage_key : str
            Storage key (path) where file will be stored

        Raises
        ------
        Exception
            If upload fails
        """
        pass


class S3StorageClient(StorageClient):
    """AWS S3 storage client implementation."""

    def __init__(self, bucket: str, region: Optional[str], prefix: str):
        """
        Initialize S3 storage client.

        Parameters
        ----------
        bucket : str
            S3 bucket name
        region : Optional[str]
            AWS region (optional, uses environment or default)
        prefix : str
            Base prefix for all storage keys
        """
        try:
            import boto3
        except ImportError:
            raise ImportError(
                "boto3 is required for AWS S3 storage. Install with: pip install darwin-py[storage_aws]"
            )

        # Use region from ObjectStore if available, otherwise from env or default
        session_config = {}
        if region:
            session_config["region_name"] = region
        elif os.getenv("AWS_REGION"):
            session_config["region_name"] = os.getenv("AWS_REGION")

        self.s3_client = boto3.client("s3", **session_config)
        self.bucket = bucket
        self.prefix = prefix

    def upload_file(self, local_path: str, storage_key: str) -> None:
        """Upload file to S3."""

        # Handle gzip content encoding
        extra_args = {}
        if local_path.endswith(".gz"):
            extra_args = {"ContentEncoding": "gzip"}

        self.s3_client.upload_file(
            local_path, self.bucket, storage_key, ExtraArgs=extra_args
        )


class GCSStorageClient(StorageClient):
    """Google Cloud Storage client implementation."""

    def __init__(self, bucket: str, prefix: str):
        """
        Initialize GCS storage client.

        Parameters
        ----------
        bucket : str
            GCS bucket name
        prefix : str
            Base prefix for all storage keys
        """
        try:
            from google.cloud import storage
        except ImportError:
            raise ImportError(
                "google-cloud-storage is required for GCS storage. Install with: pip install darwin-py[storage_gcp]"
            )

        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(bucket)
        self.prefix = prefix

    def upload_file(self, local_path: str, storage_key: str) -> None:
        """Upload file to GCS."""

        blob = self.bucket.blob(storage_key)

        # Handle gzip content encoding
        if local_path.endswith(".gz"):
            blob.content_encoding = "gzip"

        blob.upload_from_filename(local_path)


class AzureStorageClient(StorageClient):
    """Azure Blob Storage client implementation."""

    def __init__(self, account_name: str, container: str, prefix: str):
        """
        Initialize Azure storage client.

        Parameters
        ----------
        account_name : str
            Azure storage account name
        container : str
            Azure container name
        prefix : str
            Base prefix for all storage keys (within the container)
        """
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError:
            raise ImportError(
                "azure-storage-blob is required for Azure storage. Install with: pip install darwin-py[storage_azure]"
            )

        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")

        if connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                connection_string
            )
        else:
            # Use account name from ObjectStore with either account key or DefaultAzureCredential
            account_url = f"https://{account_name}.blob.core.windows.net"
            if account_key:
                # Use account key if provided
                self.blob_service_client = BlobServiceClient(
                    account_url=account_url, credential=account_key
                )
            else:
                # Use DefaultAzureCredential (supports managed identity, Azure CLI, etc.)
                try:
                    from azure.identity import DefaultAzureCredential
                except ImportError:
                    raise ImportError(
                        "azure-identity is required for DefaultAzureCredential. "
                        "Install with: pip install darwin-py[storage_azure]"
                    )
                self.blob_service_client = BlobServiceClient(
                    account_url=account_url, credential=DefaultAzureCredential()
                )

        self.container_client = self.blob_service_client.get_container_client(container)
        self.prefix = prefix

    def upload_file(self, local_path: str, storage_key: str) -> None:
        """Upload file to Azure Blob Storage."""

        blob_client = self.container_client.get_blob_client(storage_key)

        # Handle gzip content encoding
        content_settings = {}
        if local_path.endswith(".gz"):
            from azure.storage.blob import ContentSettings

            content_settings = {
                "content_settings": ContentSettings(content_encoding="gzip")
            }

        with open(local_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True, **content_settings)


def create_storage_client(object_store: ObjectStore) -> StorageClient:
    """
    Create storage client based on ObjectStore provider.

    Parameters
    ----------
    object_store : ObjectStore
        ObjectStore configuration containing provider, bucket, region, etc.

    Returns
    -------
    StorageClient
        Appropriate storage client for the provider

    Raises
    ------
    ValueError
        If provider is not supported
    """
    if object_store.provider == "aws":
        return S3StorageClient(
            bucket=object_store.bucket,
            region=object_store.region,
            prefix=object_store.prefix,
        )
    elif object_store.provider == "gcp":
        return GCSStorageClient(bucket=object_store.bucket, prefix=object_store.prefix)
    elif object_store.provider == "azure":
        # For Azure: bucket field contains storage account name
        # Prefix format: "container-name/folder-name"
        # If blank, defaults to "data" container

        if not object_store.prefix or object_store.prefix.strip() == "":
            # Default to "data" container if prefix is blank
            container = "data"
            prefix = ""
        elif "/" in object_store.prefix:
            # Extract container from first segment: "container-name/folder-name"
            container, _, prefix = object_store.prefix.partition("/")
        else:
            # No slash: treat entire prefix as container with empty path
            # E.g., "mycontainer" → container="mycontainer", prefix=""
            container = object_store.prefix
            prefix = ""

        return AzureStorageClient(
            account_name=object_store.bucket,
            container=container,
            prefix=prefix,
        )
    else:
        raise ValueError(
            f"Unsupported storage provider: {object_store.provider}. "
            f"Supported providers: aws, gcp, azure"
        )


def _get_http_status_code(exception: Exception) -> Optional[int]:
    """
    Extract HTTP status code from cloud provider exceptions.

    Handles exception patterns from AWS boto3, GCP, and Azure SDKs.

    Parameters
    ----------
    exception : Exception
        Exception to check

    Returns
    -------
    Optional[int]
        HTTP status code if found, None otherwise
    """
    # AWS boto3 - ClientError has response dict
    if hasattr(exception, "response") and isinstance(exception.response, dict):
        status_code = exception.response.get("ResponseMetadata", {}).get(
            "HTTPStatusCode"
        )
        if status_code is not None:
            return int(status_code)

    # GCP - exceptions have code attribute (integer)
    if hasattr(exception, "code"):
        code = exception.code
        if isinstance(code, int):
            return code

    # Azure - HttpResponseError has status_code attribute
    if hasattr(exception, "status_code"):
        status_code = exception.status_code
        if isinstance(status_code, int):
            return status_code

    return None


def _is_connection_or_timeout_error(exception: Exception) -> bool:
    """
    Check if exception is a connection or timeout error.

    Parameters
    ----------
    exception : Exception
        Exception to check

    Returns
    -------
    bool
        True if exception is a connection or timeout error
    """
    # Check for Python's built-in network/timeout errors
    # ConnectionError includes: ConnectionResetError, BrokenPipeError, etc.
    if isinstance(exception, (ConnectionError, TimeoutError, socket.timeout)):
        return True

    # Check the exception cause chain (SDKs often wrap underlying errors)
    cause = getattr(exception, "__cause__", None)
    if cause is not None and cause is not exception:
        return _is_connection_or_timeout_error(cause)

    return False


def is_retryable_error(exception: Exception) -> bool:
    """
    Check if an exception is a transient error that should be retried.

    Retryable errors include:
    - HTTP status codes: 408 (Request Timeout), 429 (Too Many Requests),
      500 (Internal Server Error), 502 (Bad Gateway), 503 (Service Unavailable),
      504 (Gateway Timeout)
    - Network errors: ConnectionError, ConnectionResetError, BrokenPipeError
    - Timeout errors: TimeoutError, socket.timeout

    Non-retryable errors (will NOT be retried):
    - Client errors: 400 (Bad Request), 401 (Unauthorized), 403 (Forbidden),
      404 (Not Found), etc.
    - Permission errors
    - File not found errors
    - Authentication/Authorization errors
    - Any other error not explicitly listed as retryable

    Parameters
    ----------
    exception : Exception
        Exception to check

    Returns
    -------
    bool
        True if exception is a transient error that should be retried
    """
    # Check for retryable HTTP status codes first
    status_code = _get_http_status_code(exception)
    if status_code is not None:
        return status_code in RETRYABLE_STATUS_CODES

    # Check for connection or timeout errors
    if _is_connection_or_timeout_error(exception):
        return True

    return False


def upload_with_retry(client: StorageClient, local_path: str, storage_key: str) -> None:
    """
    Upload file with exponential backoff retry logic.

    Retry behavior:
    - Exponential backoff with 20% randomization
    - Cap delay at 5 seconds
    - Total timeout at 100 seconds
    - Retry on transient errors (HTTP 408/429/5xx, connection errors, timeouts)
    - Abort immediately on non-transient errors (HTTP 4xx, permission errors, etc.)

    Parameters
    ----------
    client : StorageClient
        Storage client to use for upload
    local_path : str
        Path to local file
    storage_key : str
        Storage key where file will be stored

    Raises
    ------
    Exception
        If upload fails after retries or on non-retryable error
    """
    max_delay = 5.0
    max_time = 100.0
    base_delay = 0.1
    jitter_factor = 0.2

    start_time = time.time()
    attempt = 0

    while True:
        try:
            client.upload_file(local_path, storage_key)
            return  # Success
        except Exception as e:
            # Only retry on transient errors
            if not is_retryable_error(e):
                raise

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed >= max_time:
                raise

            # Calculate delay with jitter
            delay = min(base_delay * (2**attempt), max_delay)
            jitter = random.uniform(-jitter_factor, jitter_factor)
            delay = delay * (1 + jitter)

            print(
                f"Upload to {storage_key} failed (transient error) on attempt {attempt}; retrying in {delay:.2f} seconds..."
            )

            time.sleep(delay)
            attempt += 1


def upload_artifacts(
    object_store: ObjectStore,
    local_artifacts_dir: str,
    source_file: str,
    storage_key_prefix: str,
    max_workers: int = 10,
) -> None:
    """
    Upload all artifacts with retry logic.

    Uploads source video file and all extracted artifacts to cloud storage.
    Aborts entire operation if any upload fails.

    Parameters
    ----------
    object_store : ObjectStore
        ObjectStore configuration
    local_artifacts_dir : str
        Local directory containing extracted artifacts
    source_file : str
        Path to source video file
    storage_key_prefix : str
        Prefix for all storage keys (e.g., prefix/item_uuid/files/slot_uuid)
    max_workers : int
        Number of ThreadPoolExecutor workers (default: 10)

    Raises
    ------
    Exception
        If any upload fails after retries
    """
    client = create_storage_client(object_store)

    # Collect all files to upload
    files_to_upload = []

    # Source file
    source_filename = os.path.basename(source_file)
    files_to_upload.append((source_file, f"{storage_key_prefix}/{source_filename}"))

    # Walk artifacts directory
    for root, dirs, files in os.walk(local_artifacts_dir):
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, local_artifacts_dir)
            storage_key = f"{storage_key_prefix}/{relative_path}".replace(os.sep, "/")
            files_to_upload.append((local_path, storage_key))

    # Upload with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(upload_with_retry, client, local, key)
            for local, key in files_to_upload
        ]

        # Wait for all, abort on first failure
        for future in futures:
            future.result()  # Raises if upload failed
