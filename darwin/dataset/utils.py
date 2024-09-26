import itertools
import multiprocessing as mp
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Generator, Iterator, List, Optional, Set, Tuple, Union

import numpy as np
from PIL import Image as PILImage
from PIL import ImageOps
from rich.live import Live
from rich.progress import ProgressBar, track

import darwin.datatypes as dt

from darwin.datatypes import PathLike
from darwin.exceptions import NotFound
from darwin.importer.formats.darwin import parse_path
from darwin.utils import (
    SUPPORTED_EXTENSIONS,
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_VIDEO_EXTENSIONS,
    attempt_decode,
    get_annotation_files_from_dir,
    get_image_path_from_stream,
    is_unix_like_os,
    parse_darwin_json,
)
from darwin.utils.utils import stream_darwin_json

# E.g.: {"partition" => {"class_name" => 123}}
AnnotationDistribution = Dict[str, Counter]


def get_release_path(dataset_path: Path, release_name: Optional[str] = None) -> Path:
    """
    Given a dataset path and a release name, returns the path to the release.

    Parameters
    ----------
    dataset_path : Path
        Path to the location of the dataset on the file system.
    release_name : Optional[str], default: None
        Version of the dataset.

    Returns
    -------
    Path
        Path to the location of the dataset release on the file system.

    Raises
    ------
    NotFound
        If no dataset is found in the location provided by ``dataset_path``.
    """
    assert dataset_path is not None

    if not release_name:
        release_name = "latest"

    release_path: Path = dataset_path / "releases" / release_name
    if not release_path.exists():
        raise NotFound(
            f"Local copy of release {release_name} not found: "
            f"Pull this release from Darwin using 'darwin dataset pull {dataset_path.name}:{release_name}' "
            f"or use a different release."
        )
    return release_path


def extract_classes(
    annotations_path: Path, annotation_type: Union[str, List[str]]
) -> Tuple[Dict[str, Set[int]], Dict[int, Set[str]]]:
    """
    Given the GT as json files extracts all classes and maps images index to classes.

    Parameters
    ----------
    annotations_files : Path
        Path to the json files with the GT information of each image.
    annotation_type : Union[str, List[str]]
        Type(s) of annotation to use to extract the GT information.

    Returns
    -------
    Tuple[Dict[str, Set[int]], Dict[int, Set[str]]]
        A Tuple where the first element is a ``Dictionary`` where keys are the classes found in the
        GT and values are a list of file numbers which contain it; and the second element is
        ``Dictionary`` where keys are image indices and values are all classes
        contained in that image.
    """

    if isinstance(annotation_type, str):
        annotation_types_to_load = [annotation_type]
    else:
        annotation_types_to_load = annotation_type

    for atype in annotation_types_to_load:
        assert atype in ["bounding_box", "polygon", "tag"]

    classes: Dict[str, Set[int]] = defaultdict(set)
    indices_to_classes: Dict[int, Set[str]] = defaultdict(set)

    for i, file_name in enumerate(get_annotation_files_from_dir(annotations_path)):
        annotation_file = parse_path(Path(file_name))
        if not annotation_file:
            continue

        for annotation in annotation_file.annotations:
            if (
                annotation.annotation_class.annotation_type
                not in annotation_types_to_load
            ):
                continue

            class_name = annotation.annotation_class.name
            indices_to_classes[i].add(class_name)
            classes[class_name].add(i)

    return classes, indices_to_classes


def make_class_lists(release_path: Path) -> None:
    """
    Support function to extract classes and save the output to file.

    Parameters
    ----------
    release_path : Path
        Path to the location of the dataset on the file system.
    """
    assert release_path is not None
    if isinstance(release_path, str):
        release_path = Path(release_path)

    annotations_path = release_path / "annotations"
    assert annotations_path.exists()
    lists_path = release_path / "lists"
    lists_path.mkdir(exist_ok=True)

    for annotation_type in ["tag", "polygon", "bounding_box"]:
        fname = lists_path / f"classes_{annotation_type}.txt"
        classes, _ = extract_classes(annotations_path, annotation_type=annotation_type)
        classes_names = list(classes.keys())
        if len(classes_names) > 0:
            classes_names.sort()
            with open(str(fname), "w") as f:
                f.write("\n".join(classes_names))


def get_classes_from_file(path: Path) -> List[str]:
    """Helper function to read class names from a file."""
    if path.exists():
        return path.read_text().splitlines()
    return []


def available_annotation_types(release_path: Path) -> List[str]:
    """Returns a list of available annotation types based on the existing files."""
    files = [p.name for p in release_path.glob("lists/classes_*.txt")]
    return [f[len("classes_") : -len(".txt")] for f in files]


def get_classes(
    dataset_path: PathLike,
    release_name: Optional[str] = None,
    annotation_type: Union[str, List[str]] = "polygon",
    remove_background: bool = True,
) -> List[str]:
    """
    Given a dataset and an annotation_type returns the list of classes.

    Parameters
    ----------
    dataset_path : PathLike
        Path to the location of the dataset on the file system.
    release_name : Optional[str], default: None
        Version of the dataset.
    annotation_type : str, default: "polygon"
        The type of annotation classes [tag, polygon, bounding_box].
    remove_background : bool, default: True
        Removes the background class (if exists) from the list of classes.

    Returns
    -------
    List[str]
        List of classes in the dataset of type classes_type.
    """
    assert dataset_path is not None
    dataset_path = Path(dataset_path)
    release_path = get_release_path(dataset_path, release_name)
    if isinstance(annotation_type, str):
        annotation_types_to_load = [annotation_type]
    else:
        annotation_types_to_load = annotation_type

    classes = []  # Use a list to maintain order
    for atype in annotation_types_to_load:
        classes_file_path = release_path / f"lists/classes_{atype}.txt"

        class_per_annotations = get_classes_from_file(classes_file_path)
        if (
            remove_background
            and class_per_annotations
            and class_per_annotations[0] == "__background__"
        ):
            class_per_annotations = class_per_annotations[1:]

        for cls in class_per_annotations:
            if cls not in classes:  # Only add if it's not already in the list
                classes.append(cls)

    available_types = available_annotation_types(release_path)
    assert (
        len(classes) > 0
    ), f"No classes found for {annotation_type}. Supported types are: {', '.join(available_types)}"

    return classes


def _f(x: Any) -> Any:
    """Support function for ``pool.map()`` in ``_exhaust_generator()``."""
    if callable(x):
        return x()
    return x


def exhaust_generator(
    progress: Generator,
    count: int,
    multi_processed: bool,
    worker_count: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], List[Exception]]:
    """

    Exhausts the generator passed as parameter. Can be done multi processed if desired.
    Creates and returns a coco record from the given annotation.

    Uses ``BoxMode.XYXY_ABS`` from ``detectron2.structures`` if available, defaults to ``box_mode = 0``
    otherwise.
    Parameters
    ----------
    annotation_path : Path
        ``Path`` to the annotation file.
    annotation_type : str = "polygon"
        Type of the annotation we want to retrieve.
    image_path : Optional[Path], default: None
        ``Path`` to the image the annotation refers to.
    image_id : Optional[Union[str, int]], default: None
        Id of the image the annotation refers to.
    classes : Optional[List[str]], default: None
        Classes of the annotation.
    Returns
    -------
    Dict[str, Any]
        A coco record with the following keys:
        .. code-block:: python
            {
                "height": 100,
                "width": 100,
                "file_name": "a file name",
                "image_id": 1,
                "annotations": [ ... ]
            }
    """
    successes = []
    errors = []
    if multi_processed:
        progress_bar: ProgressBar = ProgressBar(total=count)
        responses = []

        def update(*a):
            progress_bar.completed += 1

        if worker_count is None:
            worker_count = mp.cpu_count()

        with Live(progress_bar):
            with mp.Pool(worker_count) as pool:
                for f in progress:
                    responses.append(pool.apply_async(_f, args=(f,), callback=update))
                pool.close()
                pool.join()
            for response in responses:
                try:
                    successes.append(response.get())
                except Exception as e:
                    errors.append(e)

    else:
        for f in track(progress, total=count, description="Progress"):
            try:
                successes.append(_f(f))
            except Exception as e:
                errors.append(e)
    return successes, errors


def get_coco_format_record(
    annotation_path: Path,
    annotation_type: str = "polygon",
    image_path: Optional[Path] = None,
    image_id: Optional[Union[str, int]] = None,
    classes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    assert annotation_type in ["tag", "polygon", "bounding_box"]

    try:
        from detectron2.structures import BoxMode

        box_mode = BoxMode.XYXY_ABS
    except ImportError:
        box_mode = 0

    data = parse_darwin_json(annotation_path)

    record: Dict[str, Any] = {}
    if image_path is not None:
        record["file_name"] = str(image_path)
    if image_id is not None:
        record["image_id"] = image_id

    record["height"] = data.image_height
    record["width"] = data.image_width

    objs = []
    for obj in data.annotations:
        if annotation_type != obj.annotation_class.annotation_type:
            if (
                annotation_type not in obj.data
            ):  # Allows training object detection with bboxes
                continue

        if annotation_type == "polygon":
            new_obj = create_polygon_object(obj, box_mode, classes)
        elif annotation_type == "bounding_box":
            new_obj = create_bbox_object(obj, box_mode, classes)
        else:
            continue

        objs.append(new_obj)

    record["annotations"] = objs
    return record


def create_polygon_object(obj, box_mode, classes=None):
    if "paths" in obj.data:
        paths = obj.data["paths"]
    elif "path" in obj.data:
        paths = [obj.data["path"]]
    else:
        raise ValueError("polygon path not found")

    all_px, all_py = [], []
    segmentation = []

    for path in paths:
        if len(path) < 3:
            continue
        px, py = [], []
        for point in path:
            px.append(point["x"])
            py.append(point["y"])
        poly = list(zip(px, py))
        segmentation.append(list(itertools.chain.from_iterable(poly)))
        all_px.extend(px)
        all_py.extend(py)

    new_obj = {
        "segmentation": segmentation,
        "bbox": [np.min(all_px), np.min(all_py), np.max(all_px), np.max(all_py)],
        "bbox_mode": box_mode,
        "category_id": (
            classes.index(obj.annotation_class.name)
            if classes
            else obj.annotation_class.name
        ),
        "iscrowd": 0,
    }

    return new_obj


def create_bbox_object(obj, box_mode, classes=None):
    bbox = obj.data["bounding_box"]
    new_obj = {
        "bbox": [bbox["x"], bbox["y"], bbox["x"] + bbox["w"], bbox["y"] + bbox["h"]],
        "bbox_mode": box_mode,
        "category_id": (
            classes.index(obj.annotation_class.name)
            if classes
            else obj.annotation_class.name
        ),
        "iscrowd": 0,
    }

    return new_obj


def get_annotations(
    dataset_path: PathLike,
    partition: Optional[str] = None,
    split_type: Optional[str] = "random",
    annotation_format: str = "coco",
    split: Optional[str] = "default",
    annotation_type: str = "polygon",
    release_name: Optional[str] = None,
    ignore_inconsistent_examples: bool = False,
) -> Iterator[Dict[str, Any]]:
    """
    Returns all the annotations of a given dataset and split in a single dictionary.

    Parameters
    ----------
    dataset_path : PathLike
        Path to the location of the dataset on the file system.
    partition : Optional[str], default: None
        Selects one of the partitions ``[train, val, test, None]``. If not specified, all annotations are returned.
    split_type : Optional[str], default: "random"
        Heuristic used to do the split ``[random, stratified]``. If not specified, random is used.
    annotation_format : str
        Re-formatting of the annotation when loaded ``[coco, darwin]``..
    split : Optional[str], default: "default"
        Selects the split that defines the percentages used (use 'default' to select the default split).
    annotation_type : str, default: "polygon"
        The type of annotation classes ``[tag, bounding_box, polygon]``.
    release_name : Optional[str], default: None
        Version of the dataset.
    ignore_inconsistent_examples : bool, default: False
        Ignore examples for which we have annotations, but either images are missing,
        or more than one images exist for the same annotation.
        If set to ``True``, then filter those examples out of the dataset.
        If set to ``False``, then raise an error as soon as such an example is found.

    Returns
    -------
    Iterator[Dict[str, Any]]
        Dictionary containing all the annotations of the dataset.

    Raises
    ------
    ValueError
        - If the ``partition`` given is not valid.
        - If the ``split_type`` given is not valid.
        - If the ``annotation_type`` given is not valid.
        - If an annotation has no corresponding image.
        - If an image is present with multiple extensions.
    FileNotFoundError
        If no dataset in ``dataset_path`` is found.
    """
    assert dataset_path is not None
    dataset_path = Path(dataset_path)

    release_path: Path = get_release_path(dataset_path, release_name)
    annotations_dir = release_path / "annotations"
    assert annotations_dir.exists()
    images_dir = dataset_path / "images"
    assert images_dir.exists()

    _validate_inputs(partition, split_type, annotation_type)

    classes = get_classes(
        dataset_path,
        release_name,
        annotation_type=annotation_type,
        remove_background=True,
    )

    if partition:
        annotation_filepaths = _get_annotation_filepaths_from_split(
            release_path, annotation_type, partition, split_type, split=split
        )
    else:
        annotation_filepaths = get_annotation_files_from_dir(annotations_dir)

    (
        images_paths,
        annotations_paths,
        invalid_annotation_paths,
    ) = _map_annotations_to_images(
        annotation_filepaths, images_dir, ignore_inconsistent_examples
    )

    print(f"Found {len(invalid_annotation_paths)} invalid annotations")
    for p in invalid_annotation_paths:
        print(p)

    if len(images_paths) == 0:
        raise ValueError(
            f"Could not find any {SUPPORTED_EXTENSIONS} file"
            f" in {dataset_path / 'images'}"
        )

    assert len(images_paths) == len(annotations_paths)

    yield from _load_and_format_annotations(
        images_paths, annotations_paths, annotation_format, annotation_type, classes
    )


def _validate_inputs(
    partition: Union[str, None], split_type: Union[str, None], annotation_type: str
) -> None:
    """
    Validates the input parameters for partition, split_type, and annotation_type.

    Args:
        partition (str, None): Dataset partition. Should be 'train', 'val', 'test', or None.
        split_type (str, None): Type of dataset split. Can be 'random' or 'stratified'.
        annotation_type (str): Type of annotations. Can be 'tag', 'polygon', or 'bounding_box'.

    Raises:
        ValueError: If the input parameters do not match the expected values.
    """
    if partition not in ["train", "val", "test", None]:
        raise ValueError("partition should be either 'train', 'val', 'test', or 'None'")
    if split_type not in ["random", "stratified"]:
        raise ValueError("split_type should be either 'random', or 'stratified'")
    if annotation_type not in ["tag", "polygon", "bounding_box"]:
        raise ValueError(
            "annotation_type should be either 'tag', 'bounding_box', or 'polygon'"
        )


def _get_annotation_filepaths_from_split(
    release_path: Path,
    annotation_type: str,
    partition: str,
    split_type: str,
    split: Optional[str] = "default",
) -> Generator[str, None, None]:
    """
    Determines the filpaths based on the dataset split and other parameters.

    Args:
        release_path : Path
            Path to the dataset release.
        annotation_type : str
            Type of annotations. Can be 'tag', 'polygon', or 'bounding_box'.
        partition : str
            Dataset partition. Should be 'train', 'val', 'test'.
        split_type : str
            Type of dataset split. Can be 'random' or 'stratified'.
        split : Optional[str]
            Dataset split identifier.

    Returns:
        Generator: [str, None, None]
            Filepaths for the dataset.

    Raises:
        ValueError: If the split_type is invalid.
        FileNotFoundError: If the dataset partition file is not found.
    """
    if split_type == "random":
        split_file = f"{split_type}_{partition}.txt"
    elif split_type == "stratified":
        split_file = f"{split_type}_{annotation_type}_{partition}.txt"

    split_path: Path = release_path / "lists" / str(split) / split_file

    if split_path.is_file():
        return (e.rstrip("\n\r") for e in split_path.open())
    else:
        raise FileNotFoundError(
            "Could not find a dataset partition. ",
            "To split the dataset you can use 'split_dataset' from darwin.dataset.split_manager",
        )


def _map_annotations_to_images(
    annotation_filepaths: Generator[str, None, None],
    images_dir: Path,
    ignore_inconsistent_examples: bool,
) -> Tuple[List[Path], List[Path], List[Path]]:
    """
    Maps annotations to their corresponding images based on the file stems.

    Args:
        annotation_filepaths (Generator[str, None, None]): List of annotation filepaths.
        annotations_dir (Path): Directory containing annotation files.
        images_dir (Path): Directory containing image files.
        ignore_inconsistent_examples (bool): Flag to determine if inconsistent examples should be ignored.

    Returns:
        Tuple[List[Path], List[Path], List[Path]]: Lists of paths for images, annotations, and invalid annotations respectively.

    Raises:
        ValueError: If there are inconsistencies with the annotations and images.
    """
    images_paths = []
    annotations_paths = []
    invalid_annotation_paths = []
    with_folders = any(item.is_dir() for item in images_dir.iterdir())
    for annotation_path in annotation_filepaths:
        darwin_json = stream_darwin_json(Path(annotation_path))
        image_path = get_image_path_from_stream(
            darwin_json, images_dir, Path(annotation_path), with_folders
        )
        if image_path.exists():
            images_paths.append(image_path)
            annotations_paths.append(Path(annotation_path))
            continue
        else:
            if ignore_inconsistent_examples:
                invalid_annotation_paths.append(annotation_path)
                continue
            else:
                raise ValueError(
                    f"Annotation ({annotation_path}) does not have a corresponding image"
                )

    return images_paths, annotations_paths, invalid_annotation_paths


def _load_and_format_annotations(
    images_paths: List[Path],
    annotations_paths: List[Path],
    annotation_format: str,
    annotation_type: str,
    classes: List[str],
) -> Generator[str, None, None]:
    """
    Loads and formats annotations based on the specified format and type.

    Args:
        images_paths (List[Path]): List of paths to image files.
        annotations_paths (List[Path]): List of paths to annotation files.
        annotation_format (str): Desired output format for annotations. Can be 'coco' or 'darwin'.
        annotation_type (str): Type of annotations. Can be 'tag', 'polygon', or 'bounding_box'.
        classes (List[str]): List of class names.

    Yields:
        Dict: Formatted annotation record.

    Notes:
        - If the annotation format is 'coco', video annotations cannot be loaded and will be skipped.
    """
    if annotation_format == "coco":
        images_ids = list(range(len(images_paths)))
        for annotation_path, image_path, image_id in zip(
            annotations_paths, images_paths, images_ids
        ):
            if image_path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS:
                print(
                    f"[WARNING] Cannot load video annotation into COCO format. Skipping {image_path}"
                )
                continue
            yield get_coco_format_record(
                annotation_path=annotation_path,
                annotation_type=annotation_type,
                image_path=image_path,
                image_id=image_id,
                classes=classes,
            )
    elif annotation_format == "darwin":
        for annotation_path in annotations_paths:
            record = attempt_decode(Path(annotation_path))
            yield record


def load_pil_image(path: Path, to_rgb: Optional[bool] = True) -> PILImage.Image:
    """
    Loads a PIL image and converts it into RGB (optional).

    Parameters
    ----------
    path : Path
        Path to the image file.
    to_rgb : Optional[bool], default: True
        Converts the image to RGB.

    Returns
    -------
    PILImage.Image
        The loaded image.
    """
    pic = PILImage.open(path)
    pic = ImageOps.exif_transpose(pic)
    if to_rgb:
        pic = convert_to_rgb(pic)
    return pic


def convert_to_rgb(pic: PILImage.Image) -> PILImage.Image:
    """
    Converts a PIL image to RGB.

    Parameters
    ----------
    pic : PILImage.Image
        The image to convert.

    Returns
    -------
    PIL Image
        Values between 0 and 255.

    Raises
    ------
    TypeError
        If the image given via ``pic`` has an unsupported type.
    """
    if pic.mode == "RGB":
        pass
    elif pic.mode in ("CMYK", "RGBA", "P"):
        pic = pic.convert("RGB")
    elif pic.mode == "I":
        img = (np.divide(np.array(pic, np.int32), 2**16 - 1) * 255).astype(np.uint8)
        pic = PILImage.fromarray(np.stack((img, img, img), axis=2))
    elif pic.mode == "I;16":
        img = (np.divide(np.array(pic, np.int16), 2**8 - 1) * 255).astype(np.uint8)
        pic = PILImage.fromarray(np.stack((img, img, img), axis=2))
    elif pic.mode == "L":
        img = np.array(pic).astype(np.uint8)
        pic = PILImage.fromarray(np.stack((img, img, img), axis=2))
    elif pic.mode == "1":
        pic = pic.convert("L")
        img = np.array(pic).astype(np.uint8)
        pic = PILImage.fromarray(np.stack((img, img, img), axis=2))
    else:
        raise TypeError(f"unsupported image type {pic.mode}")
    return pic


def compute_max_density(annotations_dir: Path) -> int:
    """
    Calculates the maximum density of all of the annotations in the given folder.
    Density is calculated as the number of polygons present in an annotation
    file.

    Parameters
    ----------
    annotations_dir : Path
        Directory where the annotations are present.

    Returns
    -------
    int
        The maximum density.
    """
    max_density = 0
    for annotation_path in get_annotation_files_from_dir(annotations_dir):
        annotation_density = 0
        darwin_json = parse_darwin_json(Path(annotation_path))
        for annotation in darwin_json.annotations:
            if "path" not in annotation.data and "paths" not in annotation.data:
                continue
            annotation_density += 1
        if annotation_density > max_density:
            max_density = annotation_density
    return max_density


def compute_distributions(
    annotations_dir: Path,
    split_path: Path,
    partitions: List[str] = ["train", "val", "test"],
    annotation_types: List[str] = ["polygon"],
) -> Dict[str, AnnotationDistribution]:
    """
    Builds and returns the following dictionaries:
      - class_distribution: count of all files where at least one instance of a given class exists for each partition
      - instance_distribution: count of all instances of a given class exist for each partition

    Note that this function can only be used after a dataset has been split with "stratified" strategy.

    Parameters
    ----------
    annotations_dir : Path
        Directory where the annotations are.
    split_path : Path
        Path to the split.
    partitions : List[str], default: ["train", "val", "test"]
        Partitions to use.
    annotation_types : List[str], default: ["polygon"]
        Annotation types to consider.

    Returns
    -------
    Dict[str, AnnotationDistribution]
        - class_distribution: count of all files where at least one instance of a given class exists for each partition
        - instance_distribution: count of all instances of a given class exist for each partition
    """

    class_distribution: AnnotationDistribution = {
        partition: Counter() for partition in partitions
    }
    instance_distribution: AnnotationDistribution = {
        partition: Counter() for partition in partitions
    }

    for partition in partitions:
        for annotation_type in annotation_types:
            split_file: Path = (
                split_path / f"stratified_{annotation_type}_{partition}.txt"
            )
            if not split_file.exists():
                split_file = split_path / f"random_{partition}.txt"

            annotation_filepaths: List[str] = [
                e.rstrip("\n\r") for e in split_file.open()
            ]
            for annotation_filepath in annotation_filepaths:
                if not annotation_filepath.endswith(".json"):
                    annotation_filepath = f"{annotation_filepath}.json"
                annotation_path: Path = annotations_dir / annotation_filepath
                annotation_file: Optional[dt.AnnotationFile] = parse_path(
                    annotation_path
                )
                if annotation_file is None:
                    continue

                annotation_class_names: List[str] = [
                    annotation.annotation_class.name
                    for annotation in annotation_file.annotations
                ]

                class_distribution[partition] += Counter(set(annotation_class_names))
                instance_distribution[partition] += Counter(annotation_class_names)

    return {"class": class_distribution, "instance": instance_distribution}


# https://github.com/python/cpython/blob/main/Lib/pathlib.py#L812
# TODO implemented here because it's not supported in Pythton < 3.9
def is_relative_to(path: Path, *other) -> bool:
    """
    Returns ``True`` if the path is relative to another path or ``False`` otherwise.
    It also returns ``False`` in the event of an exception, making ``False`` the default value.

    Parameters
    ----------
    path : Path
        The path to evaluate.
    other : Path
        The other path to compare against.

    Returns
    --------
    bool
    ``True`` if the path is relative to ``other`` or ``False`` otherwise.
    """
    try:
        path.relative_to(*other)
        return True
    except ValueError:
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes the given filename, removing/replacing forbiden characters.

    Parameters
    ----------
    filename : str
        The filename to sanitize.

    Returns
    -------
    str
        The sanitized filename.
    """
    chars = ["<", ">", '"', "/", "\\", "|", "?", "*"]

    if not is_unix_like_os():
        chars.append(":")

    for char in chars:
        filename = filename.replace(char, "_")

    return filename


def get_external_file_type(storage_key: str) -> Optional[str]:
    """
    Returns the type of file given a storage key.

    Parameters
    ----------
    storage_key : str
        The storage key to get the type of file from.

    Returns
    -------
    Optional[str]
        The type of file, or ``None`` if the file type is not supported.
    """
    for extension in SUPPORTED_IMAGE_EXTENSIONS:
        if storage_key.endswith(extension):
            return "image"
    if storage_key.endswith(".pdf"):
        return "pdf"
    if storage_key.endswith(".dcm"):
        return "dicom"
    for extension in SUPPORTED_VIDEO_EXTENSIONS:
        if storage_key.endswith(extension):
            return "video"
    return None


def parse_external_file_path(storage_key: str, preserve_folders: bool) -> str:
    """
    Returns the Darwin dataset path given a storage key.

    Parameters
    ----------
    storage_key : str
        The storage key to parse.
    preserve_folders : bool
        Whether to preserve folders or place the file in the Dataset root.

    Returns
    -------
    str
        The parsed external file path.
    """
    if not preserve_folders:
        return "/"
    return "/" + "/".join(storage_key.split("/")[:-1])


def get_external_file_name(storage_key: str) -> str:
    """
    Returns the name of the file given a storage key.

    Parameters
    ----------
    storage_key : str
        The storage key to get the file name from.

    Returns
    -------
    str
        The name of the file.
    """
    if "/" not in storage_key:
        return storage_key
    return storage_key.split("/")[-1]


def chunk_items(items: List[Any], chunk_size: int = 500) -> Iterator[List[Any]]:
    """
    Splits the list of items into chunks of specified size.

    Parameters
    ----------
    items : List[Any]
        The list of items to split.
    chunk_size : int, default: 500
        The size of each chunk.

    Returns
    -------
    Iterator[List[Any]]
        An iterator that yields lists of items, each of length ``chunk_size``.
    """
    return (items[i : i + chunk_size] for i in range(0, len(items), chunk_size))
