if __name__ == "__main__":
    from time import sleep

    from darwin.client import Client
    from darwin.torch import get_dataset

    client = Client.local(team_slug="v7-labs")

    dataset_id = "v7-labs/random-images"
    ds = client.get_remote_dataset(dataset_id)
    ds.pull()

    # dataset_id = "v7-labs/random-images"
    # release_name = "testexport1"

    # ds_identifier = f"{dataset_id}:{release_name}"

    # ds = client.get_remote_dataset(ds_identifier)
    # target_dataset = ds.pull()

    # ds = client.get_remote_dataset(dataset_id)
    # releases = ds.get_releases()
    # for release in releases:
    #     single_release = ds.get_release(release.name)
    #     print(f"{single_release.name} == {release.name}")
    #     assert single_release.name == release.name

    # ds2 = get_dataset(ds_identifier, dataset_type="classification")

    # print(ds)
    # for k in ds:
    #     print(k)
