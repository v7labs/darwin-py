API_KEY = key
client = Client.from_api_key(API_KEY)
dataset_slug = "test-dataset"
dataset_identifier = f {client.default_team}/{dataset_slug}"

dataset = client.get_remote_dataset(dataset_identifier)
release_name = "mj"
release = dataset.get_release(release_name)
dataset.export(release_name)
dataset.pull(release=release)