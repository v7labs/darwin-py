import itertools
import multiprocessing as mp
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Generator, Iterator, List, Optional, Set, Tuple, Union

import numpy as np
import orjson as json
from PIL import Image as PILImage
from rich.live import Live
from rich.progress import ProgressBar, track

import darwin.datatypes as dt
from darwin.datatypes import PathLike
from darwin.exceptions import NotFound
from darwin.importer.formats.darwin import parse_path
from darwin.utils import (
    SUPPORTED_EXTENSIONS,
    SUPPORTED_VIDEO_EXTENSIONS,
    is_unix_like_os,
)

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


def extract_classes(annotations_path: Path, annotation_type: str) -> Tuple[Dict[str, Set[int]], Dict[int, Set[str]]]:
    """
    Given a the GT as json files extracts all classes and an maps images index to classes.

    Parameters
    ----------
    annotations_files : Path
        Path to the json files with the GT information of each image.
    annotation_type : str
        Type of annotation to use to extract the Gt information.

    Returns
    -------
    Tuple[Dict[str, Set[int]], Dict[int, Set[str]]]
        A Tuple where the first element is a ``Dictionary`` where keys are the classes found in the
        GT and values are a list of file numbers which contain it; and the second element is
        ``Dictionary`` where keys are image indices and values are all classes
        contained in that image.
    """

    assert annotation_type in ["bounding_box", "polygon", "tag"]

    classes: Dict[str, Set[int]] = defaultdict(set)
    indices_to_classes: Dict[int, Set[str]] = defaultdict(set)

    for i, file_name in enumerate(sorted(annotations_path.glob("**/*.json"))):
        annotation_file = parse_path(file_name)
        if not annotation_file:
            continue

        for annotation in annotation_file.annotations:
            if annotation.annotation_class.annotation_type != annotation_type:
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


def get_classes(
    dataset_path: PathLike,
    release_name: Optional[str] = None,
    annotation_type: str = "polygon",
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
        The type of annotation classes [tag, polygon].
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

    classes_path = release_path / f"lists/classes_{annotation_type}.txt"
    classes = classes_path.read_text().splitlines()
    if remove_background and classes[0] == "__background__":
        classes = classes[1:]
    return classes


def _f(x: Any) -> Any:
    """Support function for ``pool.map()`` in ``_exhaust_generator()``."""
    if callable(x):
        return x()


def exhaust_generator(
    progress: Generator, count: int, multi_threaded: bool, worker_count: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Exhausts the generator passed as parameter. Can be done multi threaded if desired.

    Parameters
    ----------
    progress : Generator
        Generator to exhaust.
    count : int
        Size of the generator.
    multi_threaded : bool
        Flag for multi-threaded enabled operations.
    worker_count : Optional[int]
        Number of workers to use if multi_threaded=True. By default CPU count is used.

    Returns
    -------
    List[Dict[str, Any]
        List of responses from the generator execution.
    """
    responses = []
    if multi_threaded:
        progress_bar: ProgressBar = ProgressBar(total=count)

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
            responses = [response.get() for response in responses if response.successful()]
    else:
        for f in track(progress, total=count, description="Progress"):
            responses.append(_f(f))
    return responses


def get_coco_format_record(
    annotation_path: Path,
    annotation_type: str = "polygon",
    image_path: Optional[Path] = None,
    image_id: Optional[Union[str, int]] = None,
    classes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
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
    assert annotation_type in ["tag", "polygon", "bounding_box"]
    try:
        from detectron2.structures import BoxMode

        box_mode = BoxMode.XYXY_ABS
    except ImportError:
        box_mode = 0

    with annotation_path.open() as f:
        data = json.loads(f.read())
    height, width = data["image"]["height"], data["image"]["width"]
    annotations = data["annotations"]

    record: Dict[str, Any] = {}
    if image_path is not None:
        record["file_name"] = str(image_path)
    if image_id is not None:
        record["image_id"] = image_id
    record["height"] = height
    record["width"] = width

    objs = []
    for obj in annotations:
        px, py = [], []
        if annotation_type not in obj:
            continue

        if classes:
            category = classes.index(obj["name"])
        else:
            category = obj["name"]
        new_obj = {"bbox_mode": box_mode, "category_id": category, "iscrowd": 0}

        if annotation_type == "polygon":
            for point in obj["polygon"]["path"]:
                px.append(point["x"])
                py.append(point["y"])
            poly = [(x, y) for x, y in zip(px, py)]
            if len(poly) < 3:  # Discard polyhons with less than 3 points
                continue
            new_obj["segmentation"] = [list(itertools.chain.from_iterable(poly))]
            new_obj["bbox"] = [np.min(px), np.min(py), np.max(px), np.max(py)]
        elif annotation_type == "bounding_box":
            bbox = obj["bounding_box"]
            new_obj["bbox"] = [bbox["x"], bbox["y"], bbox["x"] + bbox["w"], bbox["y"] + bbox["h"]]

        objs.append(new_obj)
    record["annotations"] = objs
    return record


def get_annotations(
    dataset_path: PathLike,
    partition: Optional[str] = None,
    split: Optional[str] = "default",
    split_type: Optional[str] = None,
    annotation_type: str = "polygon",
    release_name: Optional[str] = None,
    annotation_format: Optional[str] = "coco",
    ignore_inconsistent_examples: bool = False,
) -> Iterator[Dict[str, Any]]:
    """
    Returns all the annotations of a given dataset and split in a single dictionary.

    Parameters
    ----------
    dataset_path : PathLike
        Path to the location of the dataset on the file system.
    partition : Optional[str], default: None
        Selects one of the partitions ``[train, val, test]``.
    split : Optional[str], default: "default"
        Selects the split that defines the percentages used (use 'default' to select the default split).
    split_type : Optional[str], default: None
        Heuristic used to do the split ``[random, stratified, None]``.
    annotation_type : str, default: "polygon"
        The type of annotation classes ``[tag, bounding_box, polygon]``.
    release_name : Optional[str], default: None
        Version of the dataset.
    annotation_format : Optional[str], default: "coco"
        Re-formatting of the annotation when loaded ``[coco, darwin]``.
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

    if partition not in ["train", "val", "test", None]:
        raise ValueError("partition should be either 'train', 'val', 'test', or None")
    if split_type not in ["random", "stratified", None]:
        raise ValueError("split_type should be either 'random', 'stratified', or None")
    if annotation_type not in ["tag", "polygon", "bounding_box"]:
        raise ValueError("annotation_type should be either 'tag', 'bounding_box', or 'polygon'")

    # Get the list of classes
    classes = get_classes(dataset_path, release_name, annotation_type=annotation_type, remove_background=True)
    # Get the list of stems
    if partition:
        # Get the split
        if split_type is None:
            split_file = f"{partition}.txt"
        elif split_type == "random":
            split_file = f"{split_type}_{partition}.txt"
        elif split_type == "stratified":
            split_file = f"{split_type}_{annotation_type}_{partition}.txt"
        else:
            raise ValueError(f"Invalid split_type ({split_type})")

        split_path: Path = release_path / "lists" / str(split) / split_file

        if split_path.is_file():
            stems: Iterator[str] = (e.rstrip("\n\r") for e in split_path.open())
        else:
            raise FileNotFoundError(
                f"Could not find a dataset partition. ",
                f"To split the dataset you can use 'split_dataset' from darwin.dataset.split_manager",
            )
    else:
        # If the partition is not specified, get all the annotations
        stems = (e.stem for e in annotations_dir.glob("**/*.json"))

    images_paths = []
    annotations_paths = []

    # Find all the annotations and their corresponding images
    invalid_annotation_paths = []
    for stem in stems:
        annotation_path = annotations_dir / f"{stem}.json"
        images = []
        for ext in SUPPORTED_EXTENSIONS:
            image_path = images_dir / f"{stem}{ext}"
            if image_path.exists():
                images.append(image_path)
                continue
            image_path = images_dir / f"{stem}{ext.upper()}"
            if image_path.exists():
                images.append(image_path)

        image_count = len(images)
        if image_count != 1 and ignore_inconsistent_examples:
            invalid_annotation_paths.append(annotation_path)
            continue
        elif image_count < 1:
            raise ValueError(f"Annotation ({annotation_path}) does not have a corresponding image")
        elif image_count > 1:
            raise ValueError(f"Image ({stem}) is present with multiple extensions. This is forbidden.")

        images_paths.append(images[0])
        annotations_paths.append(annotation_path)

    print(f"Found {len(invalid_annotation_paths)} invalid annotations")
    for p in invalid_annotation_paths:
        print(p)

    if len(images_paths) == 0:
        raise ValueError(f"Could not find any {SUPPORTED_EXTENSIONS} file" f" in {dataset_path / 'images'}")

    assert len(images_paths) == len(annotations_paths)

    # Load and re-format all the annotations
    if annotation_format == "coco":
        images_ids = list(range(len(images_paths)))
        for annotation_path, image_path, image_id in zip(annotations_paths, images_paths, images_ids):
            if image_path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS:
                print(f"[WARNING] Cannot load video annotation into COCO format. Skipping {image_path}")
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
            with annotation_path.open() as f:
                record = json.loads(f.read())
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
    Density is calculated as the number of polygons / complex_polygons present in an annotation
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
    for annotation_path in annotations_dir.glob("**/*.json"):
        annotation_density = 0
        with open(annotation_path) as f:
            darwin_json = json.loads(f.read())
            for annotation in darwin_json["annotations"]:
                if "polygon" not in annotation and "complex_polygon" not in annotation:
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

    class_distribution: AnnotationDistribution = {partition: Counter() for partition in partitions}
    instance_distribution: AnnotationDistribution = {partition: Counter() for partition in partitions}

    for partition in partitions:
        for annotation_type in annotation_types:
            split_file: Path = split_path / f"stratified_{annotation_type}_{partition}.txt"
            if not split_file.exists():
                split_file = split_path / f"random_{partition}.txt"
            stems: List[str] = [e.rstrip("\n\r") for e in split_file.open()]

            for stem in stems:
                annotation_path: Path = annotations_dir / f"{stem}.json"
                annotation_file: Optional[dt.AnnotationFile] = parse_path(annotation_path)

                if annotation_file is None:
                    continue

                annotation_class_names: List[str] = [
                    annotation.annotation_class.name for annotation in annotation_file.annotations
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
