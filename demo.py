
from darwin.client import Client
from darwin.exceptions import NameTaken

API_KEY = "ZwK7GN3.d5oHxwW-aLBvHJp4TpjJjXZ_Ac_iVct9"


def create_or_get_remote_dataset(client, dataset_slug):
    dataset_identifier = f"{client.default_team}/{dataset_slug}"
    try:
        dataset = client.create_dataset(dataset_slug)
    except NameTaken:
        dataset = client.get_remote_dataset(dataset_identifier)
    return dataset


def maybe_create_annotation_class(dataset, name, main_type):
    try:
        dataset.create_annotation_class(name, main_type)
    except NameTaken:
        pass


if __name__ == "__main__":
    client = Client.from_api_key(API_KEY)
    
    dataset = create_or_get_remote_dataset(client, "test-dataset")

    dataset.push(["./1.jpg"])
    dataset.push(["./video.mp4"], fps=5)

    # Supported types
    #   - 'bounding_box'
    #   - 'keypoint'
    #   - 'cuboid'
    #   - 'line'
    #   - 'tag'
    #   - 'polygon'
    #   - 'ellipse'
    #
    # Unsupported types
    #   - 'skeleton'
    #   - all sub annotation types
    maybe_create_annotation_class(dataset, "tag_label", "tag")
    maybe_create_annotation_class(dataset, "polygon_label", "polygon")
    maybe_create_annotation_class(dataset, "bounding_box_label", "bounding_box")
    maybe_create_annotation_class(dataset, "ellipse_label", "ellipse")

    dataset.pull()
