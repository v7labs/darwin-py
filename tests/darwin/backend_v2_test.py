"""
Tests for darwin.backend_v2 module.

Tests cover:
- register_readonly_items API method
- Request payload structure
- Error handling
"""

from unittest.mock import MagicMock

import pytest


class TestBackendV2RegisterReadonlyItems:
    """Tests for register_readonly_items method."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Darwin client."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": [], "blocked_items": []}
        client._post_raw = MagicMock(return_value=mock_response)
        return client

    @pytest.fixture
    def backend_v2(self, mock_client):
        """Create a BackendV2 instance with mock client."""
        from darwin.backend_v2 import BackendV2

        return BackendV2(mock_client, default_team="default-team")

    def test_calls_correct_endpoint(self, backend_v2, mock_client):
        """Test that the correct API endpoint is called."""
        payload = {
            "items": [{"name": "video.mp4", "slots": []}],
            "dataset_slug": "test-dataset",
            "storage_slug": "test-storage",
        }

        backend_v2.register_readonly_items(payload=payload, team_slug="my-team")

        mock_client._post_raw.assert_called_once()
        call_args = mock_client._post_raw.call_args
        assert "/v2/teams/my-team/items/register_existing_readonly" in call_args[0][0]
        assert call_args[0][1] == payload

    def test_uses_default_team_slug_when_not_provided(self, backend_v2, mock_client):
        """Test that default team slug is used when not explicitly provided."""
        payload = {"items": [], "dataset_slug": "ds", "storage_slug": "storage"}

        backend_v2.register_readonly_items(payload=payload)

        mock_client._post_raw.assert_called_once()
        call_args = mock_client._post_raw.call_args
        assert (
            "/v2/teams/default-team/items/register_existing_readonly" in call_args[0][0]
        )

    def test_returns_api_response(self, backend_v2, mock_client):
        """Test that API response is returned correctly."""
        expected_response = {
            "items": [{"id": "123", "name": "video.mp4"}],
            "blocked_items": [{"name": "dup.mp4", "slots": [{"reason": "duplicate"}]}],
        }
        mock_client._post_raw.return_value.json.return_value = expected_response

        payload = {"items": [], "dataset_slug": "ds", "storage_slug": "storage"}
        result = backend_v2.register_readonly_items(payload=payload, team_slug="team")

        assert result == expected_response

    def test_payload_contains_required_fields(self, backend_v2, mock_client):
        """Test that payload structure is passed correctly."""
        items = [
            {
                "name": "test_video.mp4",
                "path": "/videos",
                "slots": [
                    {
                        "slot_name": "test_video.mp4",
                        "storage_key": "prefix/item/files/slot/test_video.mp4",
                        "file_name": "test_video.mp4",
                        "fps": 30.0,
                        "frame_count": 100,
                        "width": 1920,
                        "height": 1080,
                        "size_bytes": 1000000,
                    }
                ],
            }
        ]
        payload = {
            "items": items,
            "dataset_slug": "my-dataset",
            "storage_slug": "my-storage",
        }

        backend_v2.register_readonly_items(payload=payload, team_slug="team")

        # Verify the payload was passed as-is
        call_args = mock_client._post_raw.call_args
        assert call_args[0][1]["items"] == items
        assert call_args[0][1]["dataset_slug"] == "my-dataset"
        assert call_args[0][1]["storage_slug"] == "my-storage"


class TestBackendV2RegisterItems:
    """Tests for register_items method (existing functionality)."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Darwin client."""
        client = MagicMock()
        client._post_raw = MagicMock(return_value={"items": [], "blocked_items": []})
        return client

    @pytest.fixture
    def backend_v2(self, mock_client):
        """Create a BackendV2 instance with mock client."""
        from darwin.backend_v2 import BackendV2

        return BackendV2(mock_client, default_team="default-team")

    def test_register_items_calls_non_readonly_endpoint(self, backend_v2, mock_client):
        """Test that register_items uses the non-readonly endpoint."""
        payload = {"items": [], "dataset_slug": "ds", "storage_slug": "storage"}

        backend_v2.register_items(payload=payload, team_slug="team")

        mock_client._post_raw.assert_called_once()
        call_args = mock_client._post_raw.call_args
        assert "/v2/teams/team/items/register_existing" in call_args[0][0]
        assert "readonly" not in call_args[0][0]
