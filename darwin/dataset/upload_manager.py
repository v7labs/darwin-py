import functools
import itertools
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import requests

from darwin.exceptions import UnsupportedFileType
from darwin.utils import SUPPORTED_IMAGE_EXTENSIONS, SUPPORTED_VIDEO_EXTENSIONS


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
        if suffix in SUPPORTED_IMAGE_EXTENSIONS:
            images.append(file_path)
        elif suffix in SUPPORTED_VIDEO_EXTENSIONS:
            videos.append(file_path)
        else:
            raise UnsupportedFileType(file_path)
    return images, videos


def add_files_to_dataset(
        client: "Client",
        dataset_id: str,
        filenames: List[Path],
        fps: Optional[int] = 1
):
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
        Number of file per seconds to upload
    Returns
    -------

    """
    if not filenames:
        raise ValueError(f"Invalid list of file names ({filenames}")

    generators = []
    for filenames_chunk in chunk_filenames(filenames, 10):
        images, videos = _split_on_file_type(filenames_chunk)
        data = client.put(
            endpoint = f"/datasets/{dataset_id}",
            payload = {"image_filenames": [image.name for image in images],
                       "videos": [{"fps": fps, "original_filename": video.name}
                                  for video in videos]}
        )
        if 'errors' in data:
            raise ValueError(f"There are errors in the put request: {data['errors']['detail']}")

        if images:
            generators.append(lambda: (
                functools.partial(
                    client.put,
                    f"/dataset_images/{upload_file_to_s3(client, image_file, images)['id']}/confirm_upload",
                    payload={},
                )
                for image_file in data["image_data"]
            ))

        if videos:
            generators.append(lambda: (
                functools.partial(
                    client.put,
                    f"/dataset_videos/{upload_file_to_s3(client, video_file, videos)['id']}/confirm_upload",
                    payload={},
                )
                for video_file in data["video_data"]
            ))
    assert generators
    return itertools.chain(*[g() for g in generators]), len(filenames)


def chunk_filenames(files: List[Path], size: int):
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
            #TODO I don't fully understand this logic. We enter here IFF there is the same
            # filename but in two different folders (which is already unusual enough?)
            # and our response is to "ship it later" with the left_over list?
            # More generally, what is the purpose of the set() i.e. why we check the uniqueness
            # of files names in one chunk?
            left_over.append(file)
        else:
            current_list.append(file)
            current_names.add(file.name)
        if len(current_list) >= size:
            yield current_list
            current_list = []
            current_names = set()
    if left_over:
        yield from chunk_filenames(left_over, size)
    if current_list:
        yield current_list


def upload_file_to_s3(
        client: "Client", file: Dict[str, Any], full_path: List[str]
) -> Dict[str, Any]:
    """Helper function: upload data to AWS S3"""
    key = file["key"]
    file_path = [path for path in full_path if Path(path).name == file["original_filename"]][0]
    image_id = file["id"]
    response = sign_upload(client, image_id, key, Path(file_path))
    signature = response["signature"]
    end_point = response["postEndpoint"]

    s3_response = upload_to_s3(signature, end_point, file_path)
    # if not str(s3_response.status_code).startswith("2"):
    #     process_response(s3_response)

    if s3_response.status_code == 400:
        print(f"Detail: Bad request when uploading to AWS S3 -- file: {file_path}")

    return {"key": key, "id": image_id}


def upload_to_s3(signature, end_point, file_path=None):
    """

    Parameters
    ----------
    signature
    end_point
    file_path

    Returns
    -------
    requests.Response
    Response of the post request
    """
    test = {"file": open(file_path, "rb")}
    return requests.post("http:" + end_point, data=signature, files=test)


def sign_upload(client, image_id, key, file_path):
    """

    Parameters
    ----------
    client
    image_id
    key
    file_path

    Returns
    -------

    """
    file_format = Path(file_path).suffix
    if file_format in SUPPORTED_IMAGE_EXTENSIONS:
        return client.post(
            f"/dataset_images/{image_id}/sign_upload?key={key}",
            payload={"filePath": str(file_path), "contentType": f"image/{file_format}"},
        )
    elif file_format in SUPPORTED_VIDEO_EXTENSIONS:
        return client.post(
            f"/dataset_videos/{image_id}/sign_upload?key={key}",
            payload={"filePath": str(file_path), "contentType": f"video/{file_format}"},
        )


def upload_annotations(
        client: "Client",
        image_mapping: Path,
        class_mapping: Path,
        annotations_path: Path
):
    """Experimental feature to upload annotations from the front end

    Parameters
    ----------
    client: Client
        Client authenticated to the team where the put request will be made
    image_mapping: Path
        Path to the json file which contains the mapping between `original file names`
        and `dataset image id` which are required in the put request to compose the endpoint
    class_mapping: Path
        Path to the json file which contains the mapping between `class name` and `class id` which
        is required in the put request to compose the payload
    annotations_path: Path
        Path to the folder which contains all the json files representing the annotations to add

    Notes
    -----
        This function is experimental and the json files `image_mapping` and `class_mapping` can
        actually only be retrieved from the backend at the moment.
    """

    # Read and prepare the image id mappings in a dict format {'class name': 'class id'}
    with image_mapping.open() as json_file:
        image_mapping = {cm['original_filename']: cm['id'] for cm in json.load(json_file)}

    # Read and prepare the class mappings in a dict format {'class name': 'class id'}
    with class_mapping.open() as json_file:
        class_mapping = {cm['name']: cm['id'] for cm in json.load(json_file)}

    # For each annotation found in the folder send out a request
    for f in annotations_path.glob("*.json"):
        with f.open() as json_file:
            # Read the annotation json file
            data = json.load(json_file)
            # Compose the payload
            payload_annotations = []
            for annotation in data['annotations']:
                # Replace the class names with class id as provided by the mapping
                class_id = class_mapping[annotation['name']]
                # Remove the name
                del (annotation['name'])
                # Compose the list of annotations as the payload wants
                payload_annotations.append({
                    'annotation_class_id':  class_id,
                    'data': annotation
                })
            payload = {"annotations": payload_annotations}
            # Compose the endpoint
            endpoint = f"dataset_images/{image_mapping[data['image']['original_filename']]}/annotations"
            response = client.put(endpoint=endpoint, payload=payload, retry=True)
            print(response)
