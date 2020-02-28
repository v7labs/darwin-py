import requests
import requests_mock

from tests.utils import setup_client


def test_init():
    client = setup_client()

    assert client.url == "https://darwin.v7labs.com/api/"
    assert client.base_url == "https://darwin.v7labs.com/"
    assert client.default_team == "team-1"


def test_get_headers():
    client = setup_client()

    default_header = {
        "Authorization": "ApiKey IwQ0zBC.eNt278rJ_yt8ZMN657NeNsv6YS_8pc5D",
        "Content-Type": "application/json",
    }

    team_2_header = {
        "Authorization": "ApiKey F8PF7xP.Vi5TONkg_L_spCWefsblI5ISSbvYJj5d",
        "Content-Type": "application/json",
    }

    assert client._get_headers() == default_header
    assert client._get_headers("team-2") == team_2_header


@requests_mock.Mocker(kw="mock")
def test_get(**kwargs):
    kwargs["mock"].get("https://darwin.v7labs.com/api/mock", json={"status": 200})

    client = setup_client()
    response = client.get("mock", "team-1")
    response_raw = client.get("mock", "team-1", raw=True)

    assert response == {"status": 200}
    assert response_raw.json() == {"status": 200}


@requests_mock.Mocker(kw="mock")
def test_put(**kwargs):
    kwargs["mock"].put("https://darwin.v7labs.com/api/mock", json={"status": 200})

    client = setup_client()
    response = client.put("mock", {}, "team-1")

    assert response == {"status": 200}


@requests_mock.Mocker(kw="mock")
def test_post(**kwargs):
    kwargs["mock"].post("https://darwin.v7labs.com/api/mock", json={"status": 200})

    client = setup_client()
    response = client.post("mock", {}, "team-1")

    assert response == {"status": 200}


# TODO test failure cases of the above tests, too
