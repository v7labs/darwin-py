from unittest.mock import Mock, patch

from requests import HTTPError

import darwin

api_key = "d7YQUUx.Gr_KwrCej3Qu43izHqIFDUIIjGUpUwYs"
dataset_identifier = "v7-labs/random-images"


def i_fail():
    raise HTTPError("404")


@patch("darwin.dataset.remote_dataset.download_all_images_from_annotations")
def test(mock_method):
    mock_method.return_value = (lambda: [i_fail, i_fail], 2)
    # mock_method.side_effect = Mock(side_effect=HTTPError("404"))
    client = darwin.Client.from_api_key(api_key=api_key)
    dataset = client.get_remote_dataset(dataset_identifier)
    release = dataset.get_release()
    dataset.pull(release=release)


if __name__ == "__main__":
    test()
