import csv
import functools
import itertools
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import requests

from darwin.dataset.utils import exhaust_generator
from darwin.exceptions import UnsupportedFileType
from darwin.utils import is_image_extension_allowed, is_video_extension_allowed

if TYPE_CHECKING:
    from darwin.client import Client

if TYPE_CHECKING:
    from darwin.client import Client


def add_files_to_dataset(client: "Client", dataset_id: str, filenames: List[Path], team: str, fps: Optional[int] = 1):
    """Helper function: upload images to an existing remote dataset

    Parameters
    ----------
    client : Client
        The client to use to communicate with the server
    dataset_id : str
        ID of the dataset to add the files to
    filenames : list[Path]
        List of filenames to upload
    fps : int
        Frame rate to split videos in.
    Returns
    -------

    """
    if not filenames:
        raise ValueError(f"Invalid list of file names ({filenames}")

    generators = []
    for filenames_chunk in _chunk_filenames(filenames, 100):
        images, videos = _split_on_file_type(filenames_chunk)
        data = client.put(
            endpoint=f"/datasets/{dataset_id}/data",
            payload={
                "image_filenames": [image.name for image in images],
                "videos": [{"fps": fps, "original_filename": video.name} for video in videos],
            },
            team=team,
        )
        if "errors" in data:
            raise ValueError(f"There are errors in the put request: {data['errors']['detail']}")
        if images:
            g = lambda images: (
                functools.partial(
                    _delayed_upload_function,
                    client=client,
                    file=image_file,
                    files_path=images,
                    endpoint_prefix="dataset_images",
                    team=team,
                )
                for image_file in data["image_data"]
            )
            generators.append(g(images))

        if videos:
            g = lambda videos: (
                functools.partial(
                    _delayed_upload_function,
                    client=client,
                    file=video_file,
                    files_path=videos,
                    endpoint_prefix="dataset_videos",
                    team=team,
                )
                for video_file in data["video_data"]
            )
            generators.append(g(videos))

    assert generators
    return itertools.chain(*generators), len(filenames)


def _split_on_file_type(files: List[Path]):
    """Splits a single list of files into images and videos based on their extension

    Parameters
    ----------
    files : list[Path]
        List of files to split according to their type

    Returns
    -------
    images, videos : list[Path]
        List of image and videos, respectively
    """
    images = []
    videos = []
    for file_path in files:
        suffix = file_path.suffix
        if is_image_extension_allowed(suffix):
            images.append(file_path)
        elif is_video_extension_allowed(suffix):
            videos.append(file_path)
        else:
            raise UnsupportedFileType(file_path)
    return images, videos


def _chunk_filenames(files: List[Path], size: int):
    """ Chunks paths in batches of size.
    No batch has any duplicates with regards to file name.
    This is needed due to a limitation in the upload api.

    Parameters
    ----------
    files : list[Path]
        List of files to chunk
    size : int
        Chunk size

    Returns
    -------
        Chunk of the list with the next `size` elements from `files`
    """
    current_list = []
    current_names = set()
    left_over = []
    for file in files:
        if file.name in current_names:
            left_over.append(file)
        else:
            current_list.append(file)
            current_names.add(file.name)
        if len(current_list) >= size:
            yield current_list
            current_list = []
            current_names = set()
    if left_over:
        yield from _chunk_filenames(left_over, size)
    if current_list:
        yield current_list


def _resolve_path(file_name: str, files_path: List[Path]):
    """Support function to resolve the path of a file given its basename and the list of paths

    Parameters
    ----------
    file_name: str
        The file name of the file
    files_path: list[Path]
        List of paths of the chunk of files being handled

    Returns
    -------
    Path
        path to the file
    """
    for p in files_path:
        if p.name == file_name:
            return p
    raise ValueError(f"File name ({file_name}) not found in the list provided")


def _delayed_upload_function(
    client: "Client", file: Dict[str, Any], files_path: List[Path], endpoint_prefix: str, team: str
):
    """
    This is a wrapper function which will be executed only once the generator is
    unrolled. It stores, however, everything it needs to be executed with the
    functools.partial design. See add_files_to_dataset()

    Parameters
    ----------
    client: Client
        Client to use to authenticate the upload
    file: dict
        The file as a response from the client.put() operation
    files_path: list[Path]
        List of paths of the chunk of files being handled
    endpoint_prefix: str
        String to prepend to the endpoint. It varies from images to videos.

    Returns
    -------
    dict
        Dictionary which contains the server response from client.put
    """
    file_path = _resolve_path(file["original_filename"], files_path)
    s3_response = upload_file_to_s3(client, file, file_path, team)
    image_id = file["id"]
    backend_response = client.put(endpoint=f"/{endpoint_prefix}/{image_id}/confirm_upload", payload={}, team=team)
    return {
        "file_path": file_path,
        "image_id": image_id,
        "s3_response_status_code": s3_response.status_code,
        "backend_response": backend_response,  # This should be the dataset_id
    }


def upload_file_to_s3(client: "Client", file: Dict[str, Any], file_path: Path, team: str) -> requests.Response:
    """Helper function: upload data to AWS S3

    Parameters
    ----------
    client: Client
        Client to use to authenticate the upload
    file: dict
        The file as a response from the client.put() operation
    file_path: Path
        Path to the file to upload on the file system

    Returns
    -------
    requests.Response
        s3 response
    """
    key = file["key"]
    image_id = file["id"]
    response = sign_upload(client, image_id, key, file_path, team)
    signature = response["signature"]
    end_point = response["postEndpoint"]
    return requests.post("http:" + end_point, data=signature, files={"file": file_path.open("rb")})


def sign_upload(client: "Client", image_id: int, key: str, file_path: Path, team: str):
    """Obtains the signed URL from the back so that we can update
    to the AWS without credentials

    Parameters
    ----------
    client: Client
        Client authenticated to the team where the put request will be made
    image_id: int
        Id of the image to upload
    key: str
        Path in the s3 bucket
    file_path: Path
        Path to the file to upload on the file system

    Returns
    -------
    dict
        Dictionary which contains the server response
    """
    file_format = file_path.suffix
    if is_image_extension_allowed(file_format):
        return client.post(
            endpoint=f"/dataset_images/{image_id}/sign_upload?key={key}",
            payload={"filePath": str(file_path), "contentType": f"image/{file_format}"},
            team=team,
        )
    elif is_video_extension_allowed(file_format):
        return client.post(
            endpoint=f"/dataset_videos/{image_id}/sign_upload?key={key}",
            payload={"filePath": str(file_path), "contentType": f"video/{file_format}"},
            team=team,
        )


def upload_annotations(
    client: "Client",
    team: str,
    image_mapping: Path,
    annotations_path: Path,
    class_mapping: Path,
    dataset_id: Optional[int] = None,
    multi_threaded: bool = True,
):
    """Experimental feature to upload annotations from the front end

    Parameters
    ----------
    client: Client
        Client authenticated to the team where the put request will be made
    team: str
        Team against which the client will make the requests
    image_mapping: Path
        Path to the json file which contains the mapping between `original file names`
        and `dataset image id` which are required in the put request to compose the endpoint
    annotations_path: Path
        Path to the folder which contains all the json files representing the annotations to add
    class_mapping: Path
        Path to the json file which contains the mapping between `class name` and `class id` which
        is required in the put request to compose the payload. If not provided, new classes
        will be created
    dataset_id: int
        Dataset ID where to upload the annotations. This is required if class_mapping is None
        or if a class present in the annotations is missing on Darwin
    multi_threaded : bool
        Uses multiprocessing to upload the dataset in parallel.
    Notes
    -----
        This function is experimental and the json files `image_mapping` and `class_mapping` can
        actually only be retrieved from the backend at the moment.
    """
    # This is where the responses from the upload function will be saved/load for resume
    responses_path = image_mapping.parent / "upload_responses.json"
    output_file_path = image_mapping.parent / "log_requests.csv"

    # Read and prepare the image id mappings in a dict format {'original filename': 'image id'}
    with image_mapping.open() as json_file:
        image_mapping = {cm["original_filename"]: cm["id"] for cm in json.load(json_file)}

    # Read and prepare the class mappings in a dict format {'class name': 'class id'}
    if class_mapping is not None:
        with class_mapping.open() as json_file:
            class_mapping = {cm["name"]: cm["id"] for cm in json.load(json_file)}
    else:
        class_mapping = {}

    # Resume
    images_id = set()

    # Check that all the classes exists
    for f in annotations_path.glob("*.json"):
        with f.open() as json_file:
            # Read the annotation json file
            data = json.load(json_file)
            image_dataset_id = image_mapping[data["image"]["original_filename"]]

            # Skip if already present
            if image_dataset_id in images_id:
                continue
            for annotation in data["annotations"]:
                # If the class is missing, create a new class on Darwin and update the mapping
                if not annotation["name"] in class_mapping:
                    if dataset_id is not None:
                        new_class = create_new_class(
                            client=client,
                            team=team,
                            annotation_type_ids=["3"],  # TODO maybe in the future allow to use polygons and BB as well
                            cropped_image={"image_id": image_dataset_id, "scale": 0.01, "x": "0", "y": "0",},
                            dataset_id=dataset_id,
                            description="",
                            expected_occurrences=[0, 1],
                            metadata=None,
                            name=annotation["name"],
                        )
                        class_mapping[new_class["name"]] = new_class["id"]
                    else:
                        raise ValueError(
                            "Dataset ID is None and a class is missing on Darwin" " (or in the provided mapping)."
                        )

    # For each annotation found in the folder send out a request
    files_to_upload = []
    for f in annotations_path.glob("*.json"):
        with f.open() as json_file:
            # Read the annotation json file
            data = json.load(json_file)
            image_dataset_id = image_mapping[data["image"]["original_filename"]]
            # Skip if already present
            if image_dataset_id in images_id:
                continue
            files_to_upload.append({"data": data, "image_dataset_id": image_dataset_id})

    generator = (
        functools.partial(
            _upload_annotation,
            class_mapping=class_mapping,
            client=client,
            team=team,
            data=element["data"],
            image_dataset_id=element["image_dataset_id"],
            output_file_path=output_file_path,
        )
        for element in files_to_upload
    )

    responses = exhaust_generator(progress=generator, count=len(files_to_upload), multi_threaded=multi_threaded)
    # Log responses to file
    if responses:
        components_labels = ["payload", "response"]
        responses = [
            {
                component_label: {k: str(v) for k, v in component.items()}
                for response in responses
                for component, component_label in zip(response, components_labels)
            }
        ]
        with responses_path.open("w") as f:
            json.dump(responses, f)


def _upload_annotation(
    class_mapping: Dict, client: "Client", team: str, data: Dict, image_dataset_id: int, output_file_path: Path,
):
    """

    Parameters
    ----------
    class_mapping: Path
        Path to the json file which contains the mapping between `class name` and `class id` which
        is required in the put request to compose the payload.
    client: Client
        Client authenticated to the team where the put request will be made
    team: str
        Team against which the client will make the requests
    data: dict
        Annotation JSON decoded
    image_dataset_id: int
        ID of the image within the dataset
    output_file_path: Path
        Path to the output file where to log the rep

    Returns
    -------
    payload: dict
        Payload used for the put request
    response : dict
        Dictionary with the response of the put request
    """
    # Compose the payload
    payload_annotations = []
    for annotation in data["annotations"]:

        # If the class is missing, create a new class on Darwin and update the mapping
        if not annotation["name"] in class_mapping:
            raise ValueError(f"Class {annotation['name']} is missing " f"in provided mapping {class_mapping}")

        # Replace the class names with class id as provided by the mapping
        class_id = class_mapping[annotation["name"]]

        # Remove the name
        del annotation["name"]
        # Compose the list of annotations as the payload wants
        payload_annotations.append({"annotation_class_id": class_id, "data": annotation})
    payload = {"annotations": payload_annotations}
    # Compose the endpoint
    endpoint = f"dataset_images/{image_dataset_id}/annotations"
    response = client.put(endpoint=endpoint, payload=payload, team=team, retry=True)
    if "error" not in response:
        with open(str(output_file_path), "a+") as file:
            writer = csv.writer(file, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow([payload, response])
    return [payload, response]


def create_new_class(
    client: "Client",
    team: str,
    annotation_type_ids: List[str],
    cropped_image: Optional[Dict],
    dataset_id: int,
    description: str,
    expected_occurrences: List[int],
    metadata: Optional[Dict],
    name: str,
):
    """Create a new class on the dataset, with the parameters provided

    Parameters
    ----------
    client: Client
        Client authenticated to the team where the put request will be made
    team: str
        Team against which the client will make the requests
    annotation_type_ids: List
        List of the annotation types. TAG is ['1'].
    cropped_image: Dict
        Description of the thumbnail for the class. Can be None.
        Example: {"image_id": 706170, "scale": 0.1455, "x": "2348", "y": "70"}
    dataset_id: int
        Dataset ID where to create the class
    description: str
        Class description. Can be empty string or None
    expected_occurrences: List
        List of integers denoting the expected occurrences.
        Example: [0, 1]
    metadata: Dict
        Metadata for the class. Example {"_color": "auto"}
    name: str
        Class name

    Returns
    -------
    response: Dict
        Client response after the request
    """
    # Sanity checks and inject default values
    if client is None:
        raise ValueError(f"Client is {client}. Invalid value.")
    if annotation_type_ids is None:
        raise ValueError(f"Annotation type IDs is {annotation_type_ids}. Invalid value.")
    if dataset_id is None:
        raise ValueError(f"Dataset ID is {dataset_id}. Invalid value.")
    if not description:
        description = ""
    if expected_occurrences is None:
        raise ValueError(f"Expected occurrences is {expected_occurrences}. Invalid value.")
    if not metadata:
        metadata = {"_color": "auto"}
    if not name:
        raise ValueError(f"Class name is {name}. Invalid value.")

    payload = {
        "annotation_type_ids": annotation_type_ids,
        "cropped_image": cropped_image,
        "dataset_id": dataset_id,
        "description": description,
        "metadata": metadata,
        "name": name,
    }

    endpoint = "annotation_classes"
    response = client.post(endpoint=endpoint, payload=payload, team=team, retry=True)
    if "errors" in response:
        raise ValueError(f"Response error: {response['errors']}")
    return response
