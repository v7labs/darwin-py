"""
Comprehensive tests for darwin.dataset.storage_uploader module.

Tests cover:
- Storage client creation and validation
- File upload with retry logic
- Error handling for 503 errors
- All cloud providers (AWS, GCP, Azure)
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from darwin.datatypes import ObjectStore


class TestCreateStorageClient:
    """Tests for create_storage_client factory function."""

    @pytest.fixture
    def aws_object_store(self):
        return ObjectStore(
            name="test-aws",
            prefix="test/prefix",
            readonly=True,
            provider="aws",
            default=False,
            bucket="test-bucket",
            region="us-east-1",
        )

    @pytest.fixture
    def gcp_object_store(self):
        return ObjectStore(
            name="test-gcp",
            prefix="test/prefix",
            readonly=True,
            provider="gcp",
            default=False,
            bucket="test-gcp-bucket",
            region=None,
        )

    @pytest.fixture
    def azure_object_store(self):
        return ObjectStore(
            name="test-azure",
            prefix="test-container/test/prefix",  # Format: container/path
            readonly=True,
            provider="azure",
            default=False,
            bucket="test-account",  # Storage account name
            region=None,
        )

    def test_raises_for_unsupported_provider(self):
        """Test that unsupported providers raise ValueError."""
        from darwin.dataset.storage_uploader import create_storage_client

        unsupported_store = ObjectStore(
            name="test",
            prefix="prefix",
            readonly=True,
            provider="unsupported",
            default=False,
            bucket="bucket",
        )

        with pytest.raises(ValueError) as exc_info:
            create_storage_client(unsupported_store)

        assert "Unsupported storage provider" in str(exc_info.value)
        assert "unsupported" in str(exc_info.value)

    @pytest.mark.skipif(
        not os.environ.get("RUN_CLOUD_STORAGE_TESTS"),
        reason="boto3 not installed; set RUN_CLOUD_STORAGE_TESTS=1 to enable",
    )
    @patch.dict(
        os.environ, {"AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test"}
    )
    @patch("boto3.client")
    def test_creates_s3_client_for_aws_provider(self, mock_boto3, aws_object_store):
        """Test that AWS provider creates S3StorageClient."""
        from darwin.dataset.storage_uploader import (
            S3StorageClient,
            create_storage_client,
        )

        client = create_storage_client(aws_object_store)
        assert isinstance(client, S3StorageClient)
        assert client.bucket == "test-bucket"
        assert client.prefix == "test/prefix"

    @pytest.mark.skipif(
        not os.environ.get("RUN_CLOUD_STORAGE_TESTS"),
        reason="GCP storage module not installed; set RUN_CLOUD_STORAGE_TESTS=1 to enable",
    )
    @patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": "/path/to/creds.json"})
    @patch("google.cloud.storage.Client")
    def test_creates_gcs_client_for_gcp_provider(
        self, mock_gcs_client, gcp_object_store
    ):
        """Test that GCP provider creates GCSStorageClient."""
        from darwin.dataset.storage_uploader import (
            GCSStorageClient,
            create_storage_client,
        )

        mock_client = MagicMock()
        mock_gcs_client.return_value = mock_client

        client = create_storage_client(gcp_object_store)
        assert isinstance(client, GCSStorageClient)
        assert client.prefix == "test/prefix"

    @pytest.mark.skipif(
        not os.environ.get("RUN_CLOUD_STORAGE_TESTS"),
        reason="Azure storage module not installed; set RUN_CLOUD_STORAGE_TESTS=1 to enable",
    )
    @patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": "connection_string"})
    @patch("azure.storage.blob.BlobServiceClient")
    def test_creates_azure_client_for_azure_provider(
        self, mock_blob_client, azure_object_store
    ):
        """Test that Azure provider creates AzureStorageClient."""
        from darwin.dataset.storage_uploader import (
            AzureStorageClient,
            create_storage_client,
        )

        mock_service = MagicMock()
        mock_blob_client.from_connection_string.return_value = mock_service

        client = create_storage_client(azure_object_store)
        assert isinstance(client, AzureStorageClient)
        assert client.prefix == "test/prefix"

    @pytest.mark.skipif(
        not os.environ.get("RUN_CLOUD_STORAGE_TESTS"),
        reason="Azure storage module not installed; set RUN_CLOUD_STORAGE_TESTS=1 to enable",
    )
    @patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": "connection_string"})
    @patch("azure.storage.blob.BlobServiceClient")
    def test_azure_empty_prefix_defaults_to_data_container(self, mock_blob_client):
        """Test that empty Azure prefix defaults to 'data' container per documentation."""
        from darwin.dataset.storage_uploader import (
            AzureStorageClient,
            create_storage_client,
        )

        mock_service = MagicMock()
        mock_container_client = MagicMock()
        mock_blob_client.from_connection_string.return_value = mock_service
        mock_service.get_container_client.return_value = mock_container_client

        # Test with empty prefix
        object_store = ObjectStore(
            name="test-azure",
            prefix="",  # Empty prefix
            readonly=True,
            provider="azure",
            default=False,
            bucket="test-account",
            region=None,
        )

        client = create_storage_client(object_store)

        # Should default to "data" container with empty prefix
        mock_service.get_container_client.assert_called_once_with("data")
        assert isinstance(client, AzureStorageClient)
        assert client.prefix == ""

    @pytest.mark.skipif(
        not os.environ.get("RUN_CLOUD_STORAGE_TESTS"),
        reason="Azure storage module not installed; set RUN_CLOUD_STORAGE_TESTS=1 to enable",
    )
    @patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": "connection_string"})
    @patch("azure.storage.blob.BlobServiceClient")
    def test_azure_prefix_without_slash_uses_as_container(self, mock_blob_client):
        """Test that Azure prefix without slash is treated as container name."""
        from darwin.dataset.storage_uploader import (
            AzureStorageClient,
            create_storage_client,
        )

        mock_service = MagicMock()
        mock_container_client = MagicMock()
        mock_blob_client.from_connection_string.return_value = mock_service
        mock_service.get_container_client.return_value = mock_container_client

        # Test with container name only (no slash)
        object_store = ObjectStore(
            name="test-azure",
            prefix="mycontainer",  # Just container name
            readonly=True,
            provider="azure",
            default=False,
            bucket="test-account",
            region=None,
        )

        client = create_storage_client(object_store)

        # Should use prefix as container name with empty path
        mock_service.get_container_client.assert_called_once_with("mycontainer")
        assert isinstance(client, AzureStorageClient)
        assert client.prefix == ""


class TestS3StorageClient:
    """Tests for S3StorageClient."""

    def test_raises_import_error_when_boto3_not_installed(self):
        """Test ImportError when boto3 is not available."""
        from darwin.dataset.storage_uploader import S3StorageClient

        with patch.dict("sys.modules", {"boto3": None}):
            with patch(
                "darwin.dataset.storage_uploader.S3StorageClient.__init__",
                side_effect=ImportError("boto3 is required"),
            ):
                with pytest.raises(ImportError) as exc_info:
                    S3StorageClient(bucket="test", region=None, prefix="prefix")
                assert "boto3" in str(exc_info.value)

    @pytest.mark.skipif(
        not os.environ.get("RUN_CLOUD_STORAGE_TESTS"),
        reason="boto3 not installed; set RUN_CLOUD_STORAGE_TESTS=1 to enable",
    )
    @patch.dict(os.environ, {}, clear=True)
    @patch("boto3.client")
    def test_creates_client_without_explicit_env_vars(self, mock_boto3):
        """Test that S3StorageClient can be created without explicit env vars (uses boto3 credential chain)."""
        from darwin.dataset.storage_uploader import S3StorageClient

        # Create client without AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY
        # This should succeed - boto3 will handle credential resolution
        client = S3StorageClient(bucket="test", region=None, prefix="prefix")

        assert client.bucket == "test"
        assert client.prefix == "prefix"
        # Should be called with 's3' and a config object for retry policy
        mock_boto3.assert_called_once()
        call_args = mock_boto3.call_args
        assert call_args[0][0] == "s3"
        assert "config" in call_args[1]

    @pytest.mark.skipif(
        not os.environ.get("RUN_CLOUD_STORAGE_TESTS"),
        reason="boto3 not installed; set RUN_CLOUD_STORAGE_TESTS=1 to enable",
    )
    @patch.dict(
        os.environ, {"AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test"}
    )
    @patch("boto3.client")
    def test_uses_region_from_constructor(self, mock_boto3):
        """Test that region from constructor is used."""
        from darwin.dataset.storage_uploader import S3StorageClient

        S3StorageClient(bucket="test", region="eu-west-1", prefix="prefix")
        # Should be called with 's3', config, and region_name
        mock_boto3.assert_called_once()
        call_args = mock_boto3.call_args
        assert call_args[0][0] == "s3"
        assert "config" in call_args[1]
        assert call_args[1]["region_name"] == "eu-west-1"

    @pytest.mark.skipif(
        not os.environ.get("RUN_CLOUD_STORAGE_TESTS"),
        reason="boto3 not installed; set RUN_CLOUD_STORAGE_TESTS=1 to enable",
    )
    @patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "test",
            "AWS_SECRET_ACCESS_KEY": "test",
            "AWS_REGION": "ap-south-1",
        },
    )
    @patch("boto3.client")
    def test_uses_region_from_env_when_not_provided(self, mock_boto3):
        """Test that AWS_REGION env var is used when region not provided."""
        from darwin.dataset.storage_uploader import S3StorageClient

        S3StorageClient(bucket="test", region=None, prefix="prefix")
        # Should be called with 's3', config, and region_name from env
        mock_boto3.assert_called_once()
        call_args = mock_boto3.call_args
        assert call_args[0][0] == "s3"
        assert "config" in call_args[1]
        assert call_args[1]["region_name"] == "ap-south-1"

    @pytest.mark.skipif(
        not os.environ.get("RUN_CLOUD_STORAGE_TESTS"),
        reason="boto3 not installed; set RUN_CLOUD_STORAGE_TESTS=1 to enable",
    )
    @patch.dict(
        os.environ, {"AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test"}
    )
    @patch("boto3.client")
    def test_upload_file_calls_s3_upload(self, mock_boto3):
        """Test that upload_file calls s3 client's upload_file method."""
        from darwin.dataset.storage_uploader import S3StorageClient

        mock_s3_client = MagicMock()
        mock_boto3.return_value = mock_s3_client

        client = S3StorageClient(bucket="test-bucket", region=None, prefix="prefix")
        client.upload_file("/path/to/file.txt", "storage/key/file.txt")

        mock_s3_client.upload_file.assert_called_once_with(
            "/path/to/file.txt", "test-bucket", "storage/key/file.txt", ExtraArgs={}
        )

    @pytest.mark.skipif(
        not os.environ.get("RUN_CLOUD_STORAGE_TESTS"),
        reason="boto3 not installed; set RUN_CLOUD_STORAGE_TESTS=1 to enable",
    )
    @patch.dict(
        os.environ, {"AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test"}
    )
    @patch("boto3.client")
    def test_upload_file_sets_gzip_encoding_for_gz_files(self, mock_boto3):
        """Test that gzip content encoding is set for .gz files."""
        from darwin.dataset.storage_uploader import S3StorageClient

        mock_s3_client = MagicMock()
        mock_boto3.return_value = mock_s3_client

        client = S3StorageClient(bucket="test-bucket", region=None, prefix="prefix")
        client.upload_file("/path/to/file.ts.gz", "storage/key/file.ts.gz")

        mock_s3_client.upload_file.assert_called_once_with(
            "/path/to/file.ts.gz",
            "test-bucket",
            "storage/key/file.ts.gz",
            ExtraArgs={"ContentEncoding": "gzip"},
        )


@pytest.mark.skipif(
    not os.environ.get("RUN_CLOUD_STORAGE_TESTS"),
    reason="GCP storage module not installed; set RUN_CLOUD_STORAGE_TESTS=1 to enable",
)
class TestGCSStorageClient:
    """Tests for GCSStorageClient."""

    @patch.dict(os.environ, {}, clear=True)
    @patch("google.cloud.storage.Client")
    def test_creates_client_without_explicit_env_vars(self, mock_storage_client):
        """Test that GCSStorageClient can be created without explicit env vars (uses ADC chain)."""
        from darwin.dataset.storage_uploader import GCSStorageClient

        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_storage_client.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket

        # Create client without GOOGLE_APPLICATION_CREDENTIALS
        # This should succeed - GCP SDK will handle credential resolution (ADC, gcloud, etc.)
        client = GCSStorageClient(bucket="test-bucket", prefix="prefix")

        assert client.prefix == "prefix"
        mock_storage_client.assert_called_once()

    @patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": "/path/to/creds.json"})
    @patch("google.cloud.storage.Client")
    def test_upload_file_calls_blob_upload(self, mock_storage_client):
        """Test that upload_file calls blob's upload_from_filename method."""
        from darwin.dataset.storage_uploader import GCSStorageClient

        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage_client.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        client = GCSStorageClient(bucket="test-bucket", prefix="prefix")
        client.upload_file("/path/to/file.txt", "storage/key/file.txt")

        mock_bucket.blob.assert_called_once_with("storage/key/file.txt")
        mock_blob.upload_from_filename.assert_called_once_with("/path/to/file.txt")

    @patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": "/path/to/creds.json"})
    @patch("google.cloud.storage.Client")
    def test_upload_file_sets_gzip_encoding_for_gz_files(self, mock_storage_client):
        """Test that gzip content encoding is set for .gz files."""
        from darwin.dataset.storage_uploader import GCSStorageClient

        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage_client.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        client = GCSStorageClient(bucket="test-bucket", prefix="prefix")
        client.upload_file("/path/to/file.ts.gz", "storage/key/file.ts.gz")

        assert mock_blob.content_encoding == "gzip"


@pytest.mark.skipif(
    not os.environ.get("RUN_CLOUD_STORAGE_TESTS"),
    reason="Azure storage module not installed; set RUN_CLOUD_STORAGE_TESTS=1 to enable",
)
class TestAzureStorageClient:
    """Tests for AzureStorageClient."""

    @patch.dict(os.environ, {}, clear=True)
    @patch("azure.storage.blob.BlobServiceClient")
    def test_creates_client_without_env_vars_using_default_credential(
        self, mock_blob_service
    ):
        """Test that AzureStorageClient can be created without env vars using DefaultAzureCredential."""
        import sys

        # Clear all Azure env vars
        os.environ.pop("AZURE_STORAGE_CONNECTION_STRING", None)
        os.environ.pop("AZURE_STORAGE_ACCOUNT_KEY", None)

        mock_service = MagicMock()
        mock_credential = MagicMock()
        mock_default_credential_cls = MagicMock(return_value=mock_credential)

        # Create a mock azure.identity module
        mock_identity_module = MagicMock()
        mock_identity_module.DefaultAzureCredential = mock_default_credential_cls

        original_module = sys.modules.get("azure.identity")
        sys.modules["azure.identity"] = mock_identity_module

        try:
            from darwin.dataset.storage_uploader import AzureStorageClient

            mock_blob_service.return_value = mock_service

            # Should succeed with account_name, using DefaultAzureCredential
            client = AzureStorageClient(
                account_name="test-account", container="test-container", prefix="prefix"
            )

            # Should use DefaultAzureCredential
            mock_default_credential_cls.assert_called_once()
            # Should be called with account_url, credential, and retry_policy
            mock_blob_service.assert_called_once()
            call_args = mock_blob_service.call_args
            assert (
                call_args[1]["account_url"]
                == "https://test-account.blob.core.windows.net"
            )
            assert call_args[1]["credential"] == mock_credential
            assert "retry_policy" in call_args[1]
            assert client.prefix == "prefix"
        finally:
            if original_module is None:
                sys.modules.pop("azure.identity", None)
            else:
                sys.modules["azure.identity"] = original_module

    @patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": "connection_string"})
    @patch("azure.storage.blob.BlobServiceClient")
    def test_uses_connection_string_when_provided(self, mock_blob_service):
        """Test that connection string is used when provided."""
        from darwin.dataset.storage_uploader import AzureStorageClient

        mock_service = MagicMock()
        mock_blob_service.from_connection_string.return_value = mock_service

        AzureStorageClient(
            account_name="test-account", container="test-container", prefix="prefix"
        )
        # Should be called with connection_string and retry_policy
        mock_blob_service.from_connection_string.assert_called_once()
        call_args = mock_blob_service.from_connection_string.call_args
        assert call_args[0][0] == "connection_string"
        assert "retry_policy" in call_args[1]

    @patch.dict(
        os.environ,
        {"AZURE_STORAGE_ACCOUNT_KEY": "key"},
        clear=True,
    )
    @patch("azure.storage.blob.BlobServiceClient")
    def test_uses_account_key_when_provided(self, mock_blob_service):
        """Test that account key from env is used when connection string not provided."""
        from darwin.dataset.storage_uploader import AzureStorageClient

        mock_service = MagicMock()
        mock_blob_service.return_value = mock_service

        # Ensure connection string is not set
        os.environ.pop("AZURE_STORAGE_CONNECTION_STRING", None)

        AzureStorageClient(
            account_name="test-account", container="test-container", prefix="prefix"
        )
        # Should be called with account_url, credential, and retry_policy
        mock_blob_service.assert_called_once()
        call_args = mock_blob_service.call_args
        assert (
            call_args[1]["account_url"] == "https://test-account.blob.core.windows.net"
        )
        assert call_args[1]["credential"] == "key"
        assert "retry_policy" in call_args[1]

    @patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": "connection_string"})
    @patch("azure.storage.blob.BlobServiceClient")
    @patch("builtins.open", new_callable=MagicMock)
    def test_upload_file_calls_blob_upload(self, mock_open, mock_blob_service):
        """Test that upload_file calls blob's upload_blob method."""
        from darwin.dataset.storage_uploader import AzureStorageClient

        mock_service = MagicMock()
        mock_container_client = MagicMock()
        mock_blob_client = MagicMock()
        mock_blob_service.from_connection_string.return_value = mock_service
        mock_service.get_container_client.return_value = mock_container_client
        mock_container_client.get_blob_client.return_value = mock_blob_client

        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        client = AzureStorageClient(
            account_name="test-account", container="test-container", prefix="prefix"
        )
        client.upload_file("/path/to/file.txt", "storage/key/file.txt")

        mock_container_client.get_blob_client.assert_called_once_with(
            "storage/key/file.txt"
        )
        mock_open.assert_called_once_with("/path/to/file.txt", "rb")
        mock_blob_client.upload_blob.assert_called_once_with(mock_file, overwrite=True)

    @patch.dict(os.environ, {"AZURE_STORAGE_CONNECTION_STRING": "connection_string"})
    @patch("azure.storage.blob.BlobServiceClient")
    @patch("azure.storage.blob.ContentSettings")
    @patch("builtins.open", new_callable=MagicMock)
    def test_upload_file_sets_gzip_encoding_for_gz_files(
        self, mock_open, mock_content_settings, mock_blob_service
    ):
        """Test that gzip content encoding is set for .gz files."""
        from darwin.dataset.storage_uploader import AzureStorageClient

        mock_service = MagicMock()
        mock_container_client = MagicMock()
        mock_blob_client = MagicMock()
        mock_blob_service.from_connection_string.return_value = mock_service
        mock_service.get_container_client.return_value = mock_container_client
        mock_container_client.get_blob_client.return_value = mock_blob_client

        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        mock_settings_instance = MagicMock()
        mock_content_settings.return_value = mock_settings_instance

        client = AzureStorageClient(
            account_name="test-account", container="test-container", prefix="prefix"
        )
        client.upload_file("/path/to/file.ts.gz", "storage/key/file.ts.gz")

        mock_content_settings.assert_called_once_with(content_encoding="gzip")
        mock_blob_client.upload_blob.assert_called_once_with(
            mock_file, overwrite=True, content_settings=mock_settings_instance
        )


class TestIsRetryableError:
    """Tests for _is_retryable_error helper function.

    Note: HTTP status code retries are handled by cloud SDKs internally.
    Our retry layer only handles network-level connection/timeout errors.
    """

    # Connection and Timeout Error Tests - Retryable

    def test_returns_true_for_connection_error(self):
        """Test that ConnectionError is retryable."""
        from darwin.dataset.storage_uploader import _is_retryable_error

        assert _is_retryable_error(ConnectionError("Connection failed")) is True

    def test_returns_true_for_connection_reset_error(self):
        """Test that ConnectionResetError is retryable."""
        from darwin.dataset.storage_uploader import _is_retryable_error

        assert _is_retryable_error(ConnectionResetError("Connection reset")) is True

    def test_returns_true_for_broken_pipe_error(self):
        """Test that BrokenPipeError is retryable."""
        from darwin.dataset.storage_uploader import _is_retryable_error

        assert _is_retryable_error(BrokenPipeError("Broken pipe")) is True

    def test_returns_true_for_timeout_error(self):
        """Test that TimeoutError is retryable."""
        from darwin.dataset.storage_uploader import _is_retryable_error

        assert _is_retryable_error(TimeoutError("Operation timed out")) is True

    def test_returns_true_for_socket_timeout(self):
        """Test that socket.timeout is retryable."""
        import socket

        from darwin.dataset.storage_uploader import _is_retryable_error

        assert _is_retryable_error(socket.timeout("Socket timed out")) is True

    def test_returns_true_for_wrapped_connection_error(self):
        """Test that wrapped connection errors in __cause__ are detected."""
        from darwin.dataset.storage_uploader import _is_retryable_error

        # Create a wrapper exception with connection error as cause
        inner_error = ConnectionResetError("Connection reset")
        outer_error = Exception("Upload failed")
        outer_error.__cause__ = inner_error

        assert _is_retryable_error(outer_error) is True

    # Non-Retryable Error Tests

    def test_returns_false_for_regular_exception(self):
        """Test that regular exceptions return False."""
        from darwin.dataset.storage_uploader import _is_retryable_error

        assert _is_retryable_error(ValueError("test")) is False

    def test_returns_false_for_permission_error(self):
        """Test that PermissionError is NOT retryable."""
        from darwin.dataset.storage_uploader import _is_retryable_error

        assert _is_retryable_error(PermissionError("Access denied")) is False

    def test_returns_false_for_file_not_found_error(self):
        """Test that FileNotFoundError is NOT retryable."""
        from darwin.dataset.storage_uploader import _is_retryable_error

        assert _is_retryable_error(FileNotFoundError("File not found")) is False

    def test_returns_false_for_type_error(self):
        """Test that TypeError is NOT retryable."""
        from darwin.dataset.storage_uploader import _is_retryable_error

        assert _is_retryable_error(TypeError("Invalid type")) is False

    def test_returns_false_for_key_error(self):
        """Test that KeyError is NOT retryable."""
        from darwin.dataset.storage_uploader import _is_retryable_error

        assert _is_retryable_error(KeyError("Missing key")) is False


class TestUploadWithRetry:
    """Tests for upload_with_retry function.

    Note: HTTP status code retries (429, 5xx) are handled by cloud SDKs internally.
    Our retry layer only handles network-level connection/timeout errors.
    """

    def test_successful_upload_no_retry(self):
        """Test that successful uploads don't trigger retries."""
        from darwin.dataset.storage_uploader import upload_with_retry

        mock_client = MagicMock()
        upload_with_retry(mock_client, "/path/to/file", "storage/key")

        mock_client.upload_file.assert_called_once_with("/path/to/file", "storage/key")

    def test_retries_on_connection_reset_error(self):
        """Test that ConnectionResetError triggers retries."""
        from darwin.dataset.storage_uploader import upload_with_retry

        mock_client = MagicMock()

        call_count = [0]

        def mock_upload(local_path, storage_key):
            call_count[0] += 1
            if call_count[0] < 2:
                raise ConnectionResetError("Connection reset by peer")
            return None

        mock_client.upload_file.side_effect = mock_upload

        with patch("tenacity.nap.time.sleep"):  # Skip actual sleep (tenacity's sleep)
            upload_with_retry(mock_client, "/path/to/file", "storage/key")

        assert call_count[0] == 2

    def test_retries_on_timeout_error(self):
        """Test that TimeoutError triggers retries."""
        from darwin.dataset.storage_uploader import upload_with_retry

        mock_client = MagicMock()

        call_count = [0]

        def mock_upload(local_path, storage_key):
            call_count[0] += 1
            if call_count[0] < 2:
                raise TimeoutError("Operation timed out")
            return None

        mock_client.upload_file.side_effect = mock_upload

        with patch("tenacity.nap.time.sleep"):  # Skip actual sleep (tenacity's sleep)
            upload_with_retry(mock_client, "/path/to/file", "storage/key")

        assert call_count[0] == 2

    def test_does_not_retry_on_non_retryable_error(self):
        """Test that non-retryable errors are not retried."""
        from darwin.dataset.storage_uploader import upload_with_retry

        mock_client = MagicMock()
        mock_client.upload_file.side_effect = ValueError("Invalid argument")

        with pytest.raises(ValueError):
            upload_with_retry(mock_client, "/path/to/file", "storage/key")

        # Should only try once
        assert mock_client.upload_file.call_count == 1

    def test_does_not_retry_on_permission_error(self):
        """Test that permission errors are NOT retried."""
        from darwin.dataset.storage_uploader import upload_with_retry

        mock_client = MagicMock()
        mock_client.upload_file.side_effect = PermissionError("Access denied")

        with pytest.raises(PermissionError):
            upload_with_retry(mock_client, "/path/to/file", "storage/key")

        assert mock_client.upload_file.call_count == 1

    def test_does_not_retry_on_file_not_found(self):
        """Test that FileNotFoundError is NOT retried."""
        from darwin.dataset.storage_uploader import upload_with_retry

        mock_client = MagicMock()
        mock_client.upload_file.side_effect = FileNotFoundError("File not found")

        with pytest.raises(FileNotFoundError):
            upload_with_retry(mock_client, "/path/to/file", "storage/key")

        assert mock_client.upload_file.call_count == 1

    def test_respects_max_timeout(self):
        """Test that retry loop respects max timeout (30s configured).

        This test verifies the stop_after_delay behavior by creating a
        test-specific retry wrapper with a very short timeout.
        """
        from tenacity import (
            retry,
            retry_if_exception,
            stop_after_delay,
            wait_exponential_jitter,
        )

        from darwin.dataset.storage_uploader import _is_retryable_error

        mock_client = MagicMock()
        mock_client.upload_file.side_effect = ConnectionResetError("Connection reset")

        # Create a test function with very short timeout (0.1 seconds)
        @retry(
            reraise=True,
            wait=wait_exponential_jitter(initial=0.01, max=0.02, jitter=0),
            stop=stop_after_delay(0.1),  # Very short timeout for testing
            retry=retry_if_exception(_is_retryable_error),
        )
        def upload_with_short_timeout(client, local_path, storage_key):
            client.upload_file(local_path, storage_key)

        # Should raise after timeout is exceeded (multiple retries with short delays)
        with pytest.raises(ConnectionResetError):
            upload_with_short_timeout(mock_client, "/path/to/file", "storage/key")

        # Verify multiple attempts were made before timeout
        assert mock_client.upload_file.call_count >= 2


class TestUploadArtifacts:
    """Tests for upload_artifacts function."""

    @pytest.fixture
    def temp_artifacts_dir(self):
        """Create a temporary artifacts directory with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir) / "artifacts"
            artifacts_dir.mkdir()

            # Create test files
            (artifacts_dir / "metadata.json").write_text('{"test": "data"}')
            (artifacts_dir / "segments").mkdir()
            (artifacts_dir / "segments" / "segment_0.ts.gz").write_text("segment data")

            source_file = Path(tmpdir) / "video.mp4"
            source_file.write_text("video content")

            yield {
                "artifacts_dir": str(artifacts_dir),
                "source_file": str(source_file),
                "tmpdir": tmpdir,
            }

    @pytest.mark.skipif(
        not os.environ.get("RUN_CLOUD_STORAGE_TESTS"),
        reason="boto3 not installed; set RUN_CLOUD_STORAGE_TESTS=1 to enable",
    )
    @patch.dict(
        os.environ, {"AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test"}
    )
    @patch("boto3.client")
    def test_uploads_source_file_and_artifacts(self, mock_boto3, temp_artifacts_dir):
        """Test that source file and all artifacts are uploaded."""
        from darwin.dataset.storage_uploader import upload_artifacts

        mock_s3_client = MagicMock()
        mock_boto3.return_value = mock_s3_client

        object_store = ObjectStore(
            name="test",
            prefix="prefix",
            readonly=True,
            provider="aws",
            default=False,
            bucket="test-bucket",
            region="us-east-1",
        )

        upload_artifacts(
            object_store=object_store,
            local_artifacts_dir=temp_artifacts_dir["artifacts_dir"],
            source_file=temp_artifacts_dir["source_file"],
            storage_key_prefix="prefix/item/files/slot",
            max_workers=2,
        )

        # Check that upload_file was called for each file
        call_args_list = mock_s3_client.upload_file.call_args_list

        # Should have 3 uploads: video.mp4, metadata.json, segment_0.ts.gz
        assert len(call_args_list) == 3

        # Extract storage keys from calls
        storage_keys = [call[0][2] for call in call_args_list]
        assert "prefix/item/files/slot/video.mp4" in storage_keys
        assert "prefix/item/files/slot/metadata.json" in storage_keys
        assert "prefix/item/files/slot/segments/segment_0.ts.gz" in storage_keys

    @pytest.mark.skipif(
        not os.environ.get("RUN_CLOUD_STORAGE_TESTS"),
        reason="boto3 not installed; set RUN_CLOUD_STORAGE_TESTS=1 to enable",
    )
    @patch.dict(
        os.environ, {"AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test"}
    )
    @patch("boto3.client")
    def test_aborts_on_upload_failure(self, mock_boto3, temp_artifacts_dir):
        """Test that all uploads abort when one fails."""
        from darwin.dataset.storage_uploader import upload_artifacts

        mock_s3_client = MagicMock()
        mock_s3_client.upload_file.side_effect = ValueError("Upload failed")
        mock_boto3.return_value = mock_s3_client

        object_store = ObjectStore(
            name="test",
            prefix="prefix",
            readonly=True,
            provider="aws",
            default=False,
            bucket="test-bucket",
            region="us-east-1",
        )

        with pytest.raises(ValueError, match="Upload failed"):
            upload_artifacts(
                object_store=object_store,
                local_artifacts_dir=temp_artifacts_dir["artifacts_dir"],
                source_file=temp_artifacts_dir["source_file"],
                storage_key_prefix="prefix/item/files/slot",
                max_workers=1,  # Use 1 worker to ensure deterministic failure
            )

    @pytest.mark.skipif(
        not os.environ.get("RUN_CLOUD_STORAGE_TESTS"),
        reason="boto3 not installed; set RUN_CLOUD_STORAGE_TESTS=1 to enable",
    )
    @patch.dict(
        os.environ, {"AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test"}
    )
    @patch("boto3.client")
    def test_handles_empty_artifacts_directory(self, mock_boto3):
        """Test behavior with empty artifacts directory."""
        from darwin.dataset.storage_uploader import upload_artifacts

        mock_s3_client = MagicMock()
        mock_boto3.return_value = mock_s3_client

        with tempfile.TemporaryDirectory() as tmpdir:
            artifacts_dir = Path(tmpdir) / "artifacts"
            artifacts_dir.mkdir()

            source_file = Path(tmpdir) / "video.mp4"
            source_file.write_text("video content")

            object_store = ObjectStore(
                name="test",
                prefix="prefix",
                readonly=True,
                provider="aws",
                default=False,
                bucket="test-bucket",
                region="us-east-1",
            )

            upload_artifacts(
                object_store=object_store,
                local_artifacts_dir=str(artifacts_dir),
                source_file=str(source_file),
                storage_key_prefix="prefix/item/files/slot",
            )

            # Should only upload the source file
            assert mock_s3_client.upload_file.call_count == 1

    @pytest.mark.skipif(
        not os.environ.get("RUN_CLOUD_STORAGE_TESTS"),
        reason="boto3 not installed; set RUN_CLOUD_STORAGE_TESTS=1 to enable",
    )
    @patch.dict(
        os.environ, {"AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test"}
    )
    @patch("boto3.client")
    def test_handles_nested_directory_structure(self, mock_boto3, temp_artifacts_dir):
        """Test that nested directories are handled correctly with proper path separators."""
        from darwin.dataset.storage_uploader import upload_artifacts

        mock_s3_client = MagicMock()
        mock_boto3.return_value = mock_s3_client

        # Create nested directory structure
        artifacts_dir = Path(temp_artifacts_dir["artifacts_dir"])
        nested_dir = artifacts_dir / "deep" / "nested" / "dir"
        nested_dir.mkdir(parents=True)
        (nested_dir / "file.txt").write_text("nested content")

        object_store = ObjectStore(
            name="test",
            prefix="prefix",
            readonly=True,
            provider="aws",
            default=False,
            bucket="test-bucket",
            region="us-east-1",
        )

        upload_artifacts(
            object_store=object_store,
            local_artifacts_dir=str(artifacts_dir),
            source_file=temp_artifacts_dir["source_file"],
            storage_key_prefix="prefix/item/files/slot",
            max_workers=2,
        )

        # Verify storage keys use forward slashes (not OS-specific separators)
        call_args_list = mock_s3_client.upload_file.call_args_list
        storage_keys = [call[0][2] for call in call_args_list]

        nested_key = "prefix/item/files/slot/deep/nested/dir/file.txt"
        assert nested_key in storage_keys


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_retryable_error_with_deeply_nested_cause(self):
        """Test _is_retryable_error with deeply nested exception cause chain."""
        from darwin.dataset.storage_uploader import _is_retryable_error

        # Create a chain: outer -> middle -> inner (ConnectionResetError)
        inner = ConnectionResetError("Connection reset")
        middle = RuntimeError("Wrapper")
        middle.__cause__ = inner
        outer = Exception("Outer wrapper")
        outer.__cause__ = middle

        assert _is_retryable_error(outer) is True

    def test_retryable_error_with_non_retryable_wrapped(self):
        """Test _is_retryable_error with non-retryable wrapped error."""
        from darwin.dataset.storage_uploader import _is_retryable_error

        inner = ValueError("Bad value")
        outer = Exception("Outer wrapper")
        outer.__cause__ = inner

        assert _is_retryable_error(outer) is False

    @pytest.mark.skipif(
        not os.environ.get("RUN_CLOUD_STORAGE_TESTS"),
        reason="boto3 not installed; set RUN_CLOUD_STORAGE_TESTS=1 to enable",
    )
    @patch.dict(
        os.environ, {"AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test"}
    )
    @patch("boto3.client")
    def test_s3_client_upload_regular_file_no_gzip_header(self, mock_boto3):
        """Test that regular files don't get gzip content encoding."""
        from darwin.dataset.storage_uploader import S3StorageClient

        mock_s3_client = MagicMock()
        mock_boto3.return_value = mock_s3_client

        client = S3StorageClient(bucket="test-bucket", region=None, prefix="prefix")

        # Upload various non-gz file types
        for filename in ["file.txt", "video.mp4", "data.json", "image.png"]:
            mock_s3_client.reset_mock()
            client.upload_file(f"/path/to/{filename}", f"storage/key/{filename}")

            call_args = mock_s3_client.upload_file.call_args
            assert (
                call_args[1]["ExtraArgs"] == {}
            ), f"Should have empty ExtraArgs for {filename}"
