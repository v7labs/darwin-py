"""
Storage uploader module for uploading video artifacts to external cloud storage.

Supports AWS S3, Google Cloud Storage, and Azure Blob Storage

Note on retry strategy:
- All cloud SDKs are configured to use their built-in robust retry logic for
  transient HTTP errors (429, 5xx) and internal timeouts.
- We add a thin outer retry layer using `tenacity` ONLY for immediate network-level
  failures (ConnectionError, socket.timeout) that may occur before SDK logic engages.
"""

import mimetypes
import os
import socket
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from tenacity import (
    retry,
    retry_if_exception,
    stop_after_delay,
    wait_exponential_jitter,
)

from darwin.datatypes import ObjectStore


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
    """AWS S3 storage client implementation.

    Uses boto3's "standard" retry mode for consistent retry behavior:
    - 5 attempts total (1 initial + 4 retries)
    - Exponential backoff with jitter
    - Retries on throttling (429), server errors (5xx), and transient connection errors
    """

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
            from botocore.config import Config
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

        retry_config = Config(
            retries={
                "mode": "standard",  # Recommended mode with exponential backoff
                "max_attempts": 5,  # 5 attempts (1 initial + 4 retries)
            }
        )

        self.s3_client = boto3.client("s3", config=retry_config, **session_config)
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
    """Google Cloud Storage client implementation.

    Uses google-cloud-storage's built-in retry (DEFAULT_RETRY):
    - Retries on 429, 500, 502, 503, 504 errors
    - Exponential backoff with jitter
    - upload_from_filename() uses DEFAULT_RETRY automatically
    """

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
    """Azure Blob Storage client implementation.

    Uses azure-storage-blob's built-in ExponentialRetry policy:
    - 5 retry attempts with exponential backoff
    - Initial backoff ~0.8s, max ~60s
    - Retries on 429, 500, 502, 503, 504 errors
    """

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
            from azure.storage.blob import BlobServiceClient, ExponentialRetry
        except ImportError:
            raise ImportError(
                "azure-storage-blob is required for Azure storage. Install with: pip install darwin-py[storage_azure]"
            )

        # Configure retry policy: 5 attempts, exponential backoff
        retry_policy = ExponentialRetry(retry_total=5)

        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")

        if connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                connection_string, retry_policy=retry_policy
            )
        else:
            # Use account name from ObjectStore with either account key or DefaultAzureCredential
            account_url = f"https://{account_name}.blob.core.windows.net"
            if account_key:
                # Use account key if provided
                self.blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=account_key,
                    retry_policy=retry_policy,
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
                    account_url=account_url,
                    credential=DefaultAzureCredential(),
                    retry_policy=retry_policy,
                )

        self.container_client = self.blob_service_client.get_container_client(container)
        self.prefix = prefix

    def upload_file(self, local_path: str, storage_key: str) -> None:
        """Upload file to Azure Blob Storage."""
        from azure.storage.blob import ContentSettings

        blob_client = self.container_client.get_blob_client(storage_key)

        # Detect content type from file extension
        content_type, _ = mimetypes.guess_type(local_path)

        # Build content settings
        settings_kwargs = {}
        if content_type:
            settings_kwargs["content_type"] = content_type
        if local_path.endswith(".gz"):
            settings_kwargs["content_encoding"] = "gzip"

        content_settings = (
            ContentSettings(**settings_kwargs) if settings_kwargs else None
        )

        with open(local_path, "rb") as data:
            blob_client.upload_blob(
                data, overwrite=True, content_settings=content_settings
            )


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


def _is_retryable_error(exception: Exception) -> bool:
    """
    Check if an exception is a transient network error that should be retried.

    This is a thin outer retry layer. Cloud SDKs handle most transient errors
    internally (429, 5xx). We retry only on:
    - Connection errors (ConnectionError, ConnectionResetError, BrokenPipeError)
    - Timeout errors (TimeoutError, socket.timeout)

    These can occur at network level before/after SDK retry logic.

    Parameters
    ----------
    exception : Exception
        Exception to check

    Returns
    -------
    bool
        True if exception should be retried
    """
    # Retryable network/connection errors
    if isinstance(exception, (ConnectionError, TimeoutError, socket.timeout)):
        return True

    # Check wrapped cause (SDKs often wrap underlying errors)
    cause = exception.__cause__
    if cause is not None and cause is not exception:
        return _is_retryable_error(cause)

    return False


@retry(
    reraise=True,
    wait=wait_exponential_jitter(initial=0.5, max=5, jitter=1),
    stop=stop_after_delay(30),
    retry=retry_if_exception(_is_retryable_error),
)
def upload_with_retry(client: StorageClient, local_path: str, storage_key: str) -> None:
    """
    Upload file with retry for connection/timeout errors.

    Cloud SDKs handle HTTP-level retries (429, 5xx) internally.
    This adds an outer retry layer for network-level failures.

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
    client.upload_file(local_path, storage_key)


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
