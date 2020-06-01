import itertools
import json
import multiprocessing as mp
import os
import sys
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Generator, Iterable, List, Optional, Union

import numpy as np
from tqdm import tqdm

from darwin.exceptions import NotFound
from darwin.utils import SUPPORTED_IMAGE_EXTENSIONS


def get_release_path(dataset_path: Path, release_name: Optional[str] = None):
    """
    Given a dataset path and a release name, returns the path to the release

    Parameters
    ----------
    dataset_path
        Path to the location of the dataset on the file system
    release_name: str
        Version of the dataset

    Returns
    -------
    release_path: Path
        Path to the location of the dataset release on the file system
    """
    assert dataset_path is not None

    if not release_name:
        release_name = "latest"
    releases_dir = dataset_path / "releases"

    if not releases_dir.exists() and (dataset_path / "annotations").exists():
        warnings.warn(
            "darwin-py has adopted a new folder structure and the old structure will be depecrated. "
            f"Migrate this dataset by running: 'darwin dataset migrate {dataset_path.name}",
            DeprecationWarning,
        )
        return dataset_path

    release_path = releases_dir / release_name
    if not release_path.exists():
        raise NotFound(
            f"Local copy of release {release_name} not found: "
            f"Pull this release from Darwin using 'darwin dataset pull {dataset_path.name}:{release_name}' "
            f"or use a different release."
        )
    return release_path


def ensure_sklearn_imported(requester):
    try:
        import sklearn  # noqa
    except ImportError:
        print(f"`{requester}` requires sklearn to be installed, pip install scikit-learn")
        sys.exit(0)


def extract_classes(annotations_path: Path, annotation_type: str):
    """
    Given a the GT as json files extracts all classes and an maps images index to classes

    Parameters
    ----------
    annotations_files: Path
        Path to the json files with the GT information of each image
    annotation_type : str
        Type of annotation to use to extract the Gt information

    Returns
    -------
    classes: dict
    Dictionary where keys are the classes found in the GT and values
    are a list of file numbers which contain it
    idx_to_classes: dict
    Dictionary where keys are image indices and values are all classes
    contained in that image
    """
    assert annotation_type in ["tag", "polygon", "bounding_box"]

    classes = defaultdict(set)
    indices_to_classes = defaultdict(set)
    annotation_files = list(annotations_path.glob("*.json"))
    for i, file_name in enumerate(annotation_files):
        with open(file_name) as f:
            annotations = json.load(f)["annotations"]
            if annotations:
                for annotation in annotations:
                    if annotation_type not in annotation:
                        continue
                    class_name = annotation["name"]
                    indices_to_classes[i].add(class_name)
                    classes[class_name].add(i)
    return classes, indices_to_classes


def make_class_lists(release_path: Path):
    """
    Support function to extract classes and save the output to file

    Parameters
    ----------
    release_path: Path
        Path to the location of the dataset on the file system
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
    dataset_path: Path,
    release_name: Optional[str] = None,
    annotation_type: str = "polygon",
    remove_background: bool = True,
):
    """
    Given a dataset and an annotation_type returns the list of classes

    Parameters
    ----------
    dataset_path
        Path to the location of the dataset on the file system
    release_name: str
        Version of the dataset
    annotation_type
        The type of annotation classes [tag, polygon]
    remove_background
        Removes the background class (if exists) from the list of classes

    Returns
    -------
    classes: list
        List of classes in the dataset of type classes_type
    """
    assert dataset_path is not None
    release_path = get_release_path(dataset_path, release_name)

    classes_file = f"classes_{annotation_type}.txt"
    classes = [e.strip() for e in open(release_path / "lists" / classes_file)]
    if remove_background and classes[0] == "__background__":
        classes = classes[1:]
    return classes


def _write_to_file(annotation_files: List, file_path: Path, split_idx: Iterable):
    """Support function for writing split indices to file

    Parameters
    ----------
    annotation_files : list
        List of json files with the GT information of each image
    file_path : Path
        Path to the file where to save the list of indices
    split_idx : Iterable
        Indices of files for this split
    """
    with open(str(file_path), "w") as f:
        for i in split_idx:
            f.write(f"{annotation_files[i].stem}\n")


def remove_cross_contamination(X_a: np.ndarray, X_b: np.ndarray, y_a: np.ndarray, y_b: np.ndarray):
    """
    Remove cross contamination present in X_a and X_b by selecting one or the other on a flip coin decision.

    The reason of cross contamination existence is
        expanded_list = [(k, c) for k, v in idx_to_classes.items() for c in v]
    in _stratify_samples(). This line creates as many entries for an image as there are lables
    attached to it. For this reason it can be that the stratification algorithm splits
    the image in both sets, A and B.
    This is very bad and this function addressed exactly that issue, removing duplicates from
    either A or B.

    Parameters
    ----------
    X_a : ndarray
    X_b : ndarray
        Arrays of elements to remove cross contamination from
    y_a : ndarray
    y_b : ndarray
        Arrays of labels relative to X_a and X_b to be filtered in the same fashion
    Returns
    -------
    X_a, X_b, y_a, y_b : ndarray
        All input parameters filtered by removing cross contamination across A and B
    """
    for a in X_a:
        if a in X_b:
            # Remove from A or B based on random chance
            if np.random.rand() > 0.5:
                # Remove ALL entries from A
                keep_locations = X_a != a
                X_a = X_a[keep_locations]
                y_a = y_a[keep_locations]
            else:
                # Remove ALL entries from B
                keep_locations = X_b != a
                X_b = X_b[keep_locations]
                y_b = y_b[keep_locations]
    return X_a, X_b, y_a, y_b


def _stratify_samples(idx_to_classes, split_seed, test_percentage, val_percentage):
    """Splits the list of indices into train, val and test according to their labels (stratified)

    Parameters
    ----------
    idx_to_classes: dict
    Dictionary where keys are image indices and values are all classes
    contained in that image
    split_seed : int
        Seed for the randomness
    val_percentage : float
        Percentage of images used in the validation set
    test_percentage : float
        Percentage of images used in the test set

    Returns
    -------
    X_train, X_val, X_test : list
        List of indices of the images for each split
    """

    ensure_sklearn_imported("split_dataset()")
    from sklearn.model_selection import train_test_split

    # Expand the list of files with all the classes
    expanded_list = [(k, c) for k, v in idx_to_classes.items() for c in v]
    # Stratify
    file_indices, labels = zip(*expanded_list)
    file_indices, labels = np.array(file_indices), np.array(labels)
    # Extract entries whose support set is 1 (it would make sklearn crash) and append the to train later
    unique_labels, count = np.unique(labels, return_counts=True)
    single_files = []
    for l in unique_labels[count == 1]:
        index = np.where(labels == l)[0][0]
        single_files.append(file_indices[index])
        labels = np.delete(labels, index)
        file_indices = np.delete(file_indices, index)
    # If file_indices or labels are empty, the following train_test_split will crash (empty train set)
    if len(file_indices) == 0 or len(labels) == 0:
        return [], [], []

    X_train, X_tmp, y_train, y_tmp = remove_cross_contamination(
        *train_test_split(
            np.array(file_indices),
            np.array(labels),
            test_size=(val_percentage + test_percentage) / 100.0,
            random_state=split_seed,
            stratify=labels,
        )
    )
    # Append files whose support set is 1 to train
    X_train = np.concatenate((X_train, np.array(single_files)), axis=0)

    if test_percentage == 0.0:
        return list(set(X_train.astype(np.int))), list(set(X_tmp.astype(np.int))), None

    X_val, X_test, y_val, y_test = remove_cross_contamination(
        *train_test_split(
            X_tmp,
            y_tmp,
            test_size=(test_percentage / (val_percentage + test_percentage)),
            random_state=split_seed,
            stratify=y_tmp,
        )
    )

    # Remove duplicates within the same set
    # NOTE: doing that earlier (e.g. in remove_cross_contamination()) would produce mathematical
    # mistakes in the class balancing between validation and test sets.
    return (
        list(set(X_train.astype(np.int))),
        list(set(X_val.astype(np.int))),
        list(set(X_test.astype(np.int))),
    )


def split_dataset(
    dataset_path: Union[Path, str],
    release_name: Optional[str] = None,
    val_percentage: Optional[float] = 10,
    test_percentage: Optional[float] = 20,
    split_seed: Optional[int] = 0,
    make_default_split: Optional[bool] = True,
    add_stratified_split: Optional[bool] = True,
):
    """
    Given a local a dataset (pulled from Darwin) creates lists of file names
    for each split for train, validation, and test.

    Parameters
    ----------
    dataset_path : Path
        Local path to the dataset
    release_name: str
        Version of the dataset
    val_percentage : float
        Percentage of images used in the validation set
    test_percentage : float
        Percentage of images used in the test set
    split_seed : int
        Fix seed for random split creation
    make_default_split: bool
        Makes this split the default split
    add_stratified_split: bool
        In addition to the random split it also adds a stratified split

    Returns
    -------
    splits : dict
        Keys are the different splits (random, tags, ...) and values are the relative file names
    """
    assert dataset_path is not None
    if isinstance(dataset_path, str):
        dataset_path = Path(dataset_path)
    release_path = get_release_path(dataset_path, release_name)

    annotation_path = release_path / "annotations"
    assert annotation_path.exists()
    annotation_files = list(annotation_path.glob("*.json"))

    # Prepare the lists folder
    lists_path = release_path / "lists"
    lists_path.mkdir(parents=True, exist_ok=True)

    # Create split id, path and final split paths
    if val_percentage is None or not 0 <= val_percentage < 100:
        raise ValueError(f"Invalid validation percentage ({val_percentage}). " f"Must be >= 0 and < 100")
    if test_percentage is None or not 0 <= test_percentage < 100:
        raise ValueError(f"Invalid test percentage ({test_percentage}). " f"Must be >= 0 and < 100")
    if not 1 <= val_percentage + test_percentage < 100:
        raise ValueError(
            f"Invalid combination of validation ({val_percentage}) "
            f"and test ({test_percentage}) percentages. Their sum must be > 1 and < 100"
        )
    if split_seed is None:
        raise ValueError("Seed is None")
    split_id = f"split_v{int(val_percentage)}_t{int(test_percentage)}"
    if split_seed != 0:
        split_id += f"_s{split_seed}"
    split_path = lists_path / split_id

    # Prepare the return value with the paths of the splits
    splits = {}
    splits["random"] = {
        "train": Path(split_path / "random_train.txt"),
        "val": Path(split_path / "random_val.txt"),
    }
    splits["stratified_tag"] = {
        "train": Path(split_path / "stratified_tag_train.txt"),
        "val": Path(split_path / "stratified_tag_val.txt"),
    }
    splits["stratified_polygon"] = {
        "train": Path(split_path / "stratified_polygon_train.txt"),
        "val": Path(split_path / "stratified_polygon_val.txt"),
    }
    splits["stratified_bounding_box"] = {
        "train": Path(split_path / "stratified_bounding_box_train.txt"),
        "val": Path(split_path / "stratified_bounding_box_val.txt"),
    }
    if test_percentage > 0.0:
        splits["random"]["test"] = Path(split_path) / "random_test.txt"
        splits["stratified_tag"]["test"] = Path(split_path / "stratified_tag_test.txt")
        splits["stratified_polygon"]["test"] = Path(split_path / "stratified_polygon_test.txt")
        splits["stratified_bounding_box"]["test"] = Path(split_path / "stratified_bounding_box_test.txt")

    # Do the actual split
    if not split_path.exists():
        os.makedirs(str(split_path), exist_ok=True)

        # RANDOM SPLIT
        # Compute split sizes
        dataset_size = sum(1 for _ in annotation_files)
        val_size = int(dataset_size * (val_percentage / 100.))
        test_size = int(dataset_size * (test_percentage / 100.))
        train_size = dataset_size - val_size - test_size
        # Slice a permuted array as big as the dataset
        np.random.seed(split_seed)
        indices = np.random.permutation(dataset_size)
        train_indices = list(indices[:train_size])
        val_indices = list(indices[train_size: train_size + val_size])
        test_indices = list(indices[train_size + val_size:])
        # Write files
        _write_to_file(annotation_files, splits["random"]["train"], train_indices)
        _write_to_file(annotation_files, splits["random"]["val"], val_indices)
        if test_percentage > 0.0:
            _write_to_file(annotation_files, splits["random"]["test"], test_indices)

        if add_stratified_split:
            # STRATIFIED SPLIT ON TAGS
            # Stratify
            classes_tag, idx_to_classes_tag = extract_classes(annotation_path, "tag")
            if len(idx_to_classes_tag) > 0:
                train_indices, val_indices, test_indices = _stratify_samples(
                    idx_to_classes_tag, split_seed, test_percentage, val_percentage
                )
                # Write files
                _write_to_file(annotation_files, splits["stratified_tag"]["train"], train_indices)
                _write_to_file(annotation_files, splits["stratified_tag"]["val"], val_indices)
                if test_percentage > 0.0:
                    _write_to_file(annotation_files, splits["stratified_tag"]["test"], test_indices)

            # STRATIFIED SPLIT ON POLYGONS
            # Stratify
            classes_polygon, idx_to_classes_polygon = extract_classes(annotation_path, "polygon")
            if len(idx_to_classes_polygon) > 0:
                train_indices, val_indices, test_indices = _stratify_samples(
                    idx_to_classes_polygon, split_seed, test_percentage, val_percentage
                )
                # Write files
                _write_to_file(annotation_files, splits["stratified_polygon"]["train"], train_indices)
                _write_to_file(annotation_files, splits["stratified_polygon"]["val"], val_indices)
                if test_percentage > 0.0:
                    _write_to_file(annotation_files, splits["stratified_polygon"]["test"], test_indices)

            # STRATIFIED SPLIT ON BOUNDING BOXES
            # Stratify
            classes_bbox, idx_to_classes_bbox = extract_classes(annotation_path, "bounding_box")
            if len(idx_to_classes_bbox) > 0:
                train_indices, val_indices, test_indices = _stratify_samples(
                    idx_to_classes_bbox, split_seed, test_percentage, val_percentage
                )
                # Write files
                _write_to_file(annotation_files, splits["stratified_bounding_box"]["train"], train_indices)
                _write_to_file(annotation_files, splits["stratified_bounding_box"]["val"], val_indices)
                if test_percentage > 0.0:
                    _write_to_file(annotation_files, splits["stratified_bounding_box"]["test"], test_indices)

    # Create symlink for default split
    split = lists_path / "default"
    if make_default_split or not split.exists():
        if split.exists():
            split.unlink()
        split.symlink_to(f"./{split_id}")

    return split_path


def _f(x):
    """Support function for pool.map() in _exhaust_generator()"""
    if callable(x):
        return x()


def exhaust_generator(progress: Generator, count: int, multi_threaded: bool):
    """Exhausts the generator passed as parameter. Can be done multi threaded if desired

    Parameters
    ----------
    progress : Generator
        Generator to exhaust
    count : int
        Size of the generator
    multi_threaded : bool
        Flag for multi-threaded enabled operations

    Returns
    -------
    List[dict]
        List of responses from the generator execution
    """
    responses = []
    if multi_threaded:
        pbar = tqdm(total=count)

        def update(*a):
            pbar.update()

        with mp.Pool(mp.cpu_count()) as pool:
            for f in progress:
                responses.append(pool.apply_async(_f, args=(f,), callback=update))
            pool.close()
            pool.join()
        responses = [response.get() for response in responses if response.successful()]
    else:
        for f in tqdm(progress, total=count, desc="Progress"):
            responses.append(_f(f))
    return responses


def get_coco_format_record(
    annotation_path: Path,
    annotation_type: str = "polygon",
    image_path: Optional[Path] = None,
    image_id: Optional[Union[str, int]] = None,
    classes: Optional[List[str]] = None,
):
    assert annotation_type in ["tag", "polygon", "bounding_box"]
    try:
        from detectron2.structures import BoxMode

        box_mode = BoxMode.XYXY_ABS
    except ImportError:
        box_mode = 0

    with annotation_path.open() as f:
        data = json.load(f)
    height, width = data["image"]["height"], data["image"]["width"]
    annotations = data["annotations"]

    record = {}
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
        new_obj = {
            "bbox_mode": box_mode,
            "category_id": category,
            "iscrowd": 0,
        }

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
    dataset_path: Union[Path, str],
    partition: Optional[str] = None,
    split: Optional[str] = None,
    split_type: Optional[str] = None,
    annotation_type: str = "polygon",
    release_name: Optional[str] = None,
    annotation_format: Optional[str] = "coco",
):
    """
    Returns all the annotations of a given dataset and split in a single dictionary

    Parameters
    ----------
    dataset_path
        Path to the location of the dataset on the file system
    partition
        Selects one of the partitions [train, val, test]
    split
        Selects the split that defines the percetages used (use 'split' to select the default split)
    split_type
        Heuristic used to do the split [random, stratified, None]
    annotation_type
        The type of annotation classes [tag, bounding_box, polygon]
    release_name: str
        Version of the dataset
    annotations_format: str
        Re-formatting of the annotation when loaded [coco, darwin]

    Returns
    -------
    dict
        Dictionary containing all the annotations of the dataset
    """
    assert dataset_path is not None
    if isinstance(dataset_path, str):
        dataset_path = Path(dataset_path)

    release_path = get_release_path(dataset_path, release_name)

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
    if split:
        # Get the split
        if split_type is None:
            split_file = f"{partition}.txt"
        elif split_type == "random":
            split_file = f"{split_type}_{partition}.txt"
        elif split_type == "stratified":
            split_file = f"{split_type}_{annotation_type}_{partition}.txt"
        split_path = release_path / "lists" / split / split_file
        if split_path.is_file():
            stems = (e.strip() for e in split_path.open())
        else:
            raise FileNotFoundError(
                f"Could not find a dataset partition. ",
                f"To split the dataset you can use 'split_dataset' from darwin.dataset.utils",
            )
    else:
        # If the split is not specified, get all the annotations
        stems = [e.stem for e in annotations_dir.glob("*.json")]

    images_paths = []
    annotations_paths = []

    # Find all the annotations and their corresponding images
    for stem in stems:
        annotation_path = annotations_dir / f"{stem}.json"
        images = []
        for ext in SUPPORTED_IMAGE_EXTENSIONS:
            image_path = images_dir / f"{stem}{ext}"
            if image_path.exists():
                images.append(image_path)
        if len(images) < 1:
            raise ValueError(f"Annotation ({annotation_path}) does not have a corresponding image")
        if len(images) > 1:
            raise ValueError(f"Image ({stem}) is present with multiple extensions. This is forbidden.")
        assert len(images) == 1
        images_paths.append(images[0])
        annotations_paths.append(annotation_path)

    if len(images_paths) == 0:
        raise ValueError(f"Could not find any {SUPPORTED_IMAGE_EXTENSIONS} file" f" in {dataset_path / 'images'}")

    assert len(images_paths) == len(annotations_paths)

    # Load and re-format all the annotations
    if annotation_format == "coco":
        images_ids = list(range(len(images_paths)))
        for annotation_path, image_path, image_id in zip(annotations_paths, images_paths, images_ids):
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
                record = json.load(f)
            yield record
