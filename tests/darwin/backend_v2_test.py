from unittest.mock import Mock, call, patch

import pytest
from requests.exceptions import HTTPError
from requests.models import Response
from tenacity import RetryError

from darwin.backend_v2 import BackendV2


class TestBackendV2:
    @patch("time.sleep", return_value=None)
    def test_register_items_retries_on_429(self, mock_sleep):
        mock_client = Mock()
        mock_response = Mock(spec=Response)
        mock_response.status_code = 429
        mock_client._post_raw.side_effect = HTTPError(response=mock_response)

        backend = BackendV2(mock_client, "team_slug")

        payload = {"key": "value"}
        with pytest.raises(RetryError):
            backend.register_items(payload)

        assert mock_client._post_raw.call_count == 10

        expected_call = call("/v2/teams/team_slug/items/register_existing", payload)
        assert mock_client._post_raw.call_args_list == [expected_call] * 10
