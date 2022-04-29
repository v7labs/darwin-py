from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import numpy as np
from darwin.dataset.utils import extract_classes, get_release_path
from darwin.datatypes import PathLike


@dataclass
class Split:
    """
    A Split object holds the state of a split as a set of attributes.
    For each split type (namely, random and stratified), the Split object will keep a record
    of paths were the splits are going to be stored as files.

    If a dataset can be split randomly, then the ``random`` attribute will be set as a
    dictionary between a particular partition (e.g.: ``train``, ``val``, ``test``) and
    the ``Path`` of the file where that partition split file is going to be stored.

    .. code-block:: python

        {
            "train": Path("/path/to/split/random_train.txt"),
            "val": Path("/path/to/split/random_val.txt"),
            "test": Path("/path/to/split/random_test.txt")
        }

    If a dataset can be split with a stratified strategy based on a given annotation type,
    then the ``stratified`` attribute will be set as a dictionary between a particular annotation type
    and a dictionary between a particular partition (e.g.: ``train``, ``val``, ``test``) and
    the ``Path`` of the file where that partition split file is going to be stored.

    .. code-block:: python

        {
            "polygon": {
                "train": Path("/path/to/split/stratified_polygon_train.txt"),
                "val": Path("/path/to/split/stratified_polygon_val.txt"),
                "test": Path("/path/to/split/stratified_polygon_test.txt")
            },
            "tag": {
                "train": Path("/path/to/split/stratified_tag_train.txt"),
                "val": Path("/path/to/split/stratified_tag_val.txt"),
                "test": Path("/path/to/split/stratified_tag_test.txt")
            }
        }

    """

    #: Stores the type of split (e.g. ``train``, ``val``, ``test``) and the file path where the
    #: split is stored if the split is of type ``random``.
    random: Optional[Dict[str, Path]] = None

    #: Stores the relation between an annotation type and the partition-filepath key value of the
    #: split if its type is ``stratified``.
    stratified: Optional[Dict[str, Dict[str, Path]]] = None

    def is_valid(self) -> bool:
        """
        Returns whether or not this split instance is valid.

        Returns
        -------
        bool
            ``True`` if this instance is valid, ``False`` otherwise.
        """
        return self.random is not None or self.stratified is not None


def split_dataset(
    dataset_path: PathLike,
    release_name: Optional[str] = None,
    val_percentage: float = 0.1,
    test_percentage: float = 0.2,
    split_seed: int = 0,
    make_default_split: bool = True,
    stratified_types: List[str] = ["bounding_box", "polygon", "tag"],
) -> Path:
    """
    Given a local a dataset (pulled from Darwin), split it by creating lists of filenames.
    The partitions to split the dataset into are called train, val and test.

    The dataset is always split randomly, and can be additionally split according to the
    stratified strategy by providing a list of stratified types.

    Requires ``scikit-learn`` to split a dataset.

    Parameters
    ----------
    dataset_path : PathLike
        Local path to the dataset.
    release_name : Optional[str], default: None
        Version of the dataset.
    val_percentage : float, default: 0.1
        Percentage of images used in the validation set.
    test_percentage : float, default: 0.2
        Percentage of images used in the test set.
    split_seed : int, default: 0
        Fix seed for random split creation.
    make_default_split : bool, default: True
        Makes this split the default split.
    stratified_types : List[str], default: ["bounding_box", "polygon", "tag"]
        List of annotation types to split with the stratified strategy.

    Returns
    -------
    Path
        Keys are the different splits (random, tags, ...) and values are the relative file names.

    Raises
    ------
    ImportError
        If ``sklearn`` is not installed.
    """
    # Requirements: scikit-learn
    try:
        import sklearn  # noqa
    except ImportError:
        raise ImportError(
            "Darwin requires scikit-learn to split a dataset. Install it using: pip install scikit-learn"
        ) from None

    _validate_split(val_percentage, test_percentage)

    # Infer release path
    if isinstance(dataset_path, str):
        dataset_path = Path(dataset_path)
    release_path = get_release_path(dataset_path, release_name)

    # List all annotation files in release
    annotation_path = release_path / "annotations"
    assert annotation_path.exists()
    annotation_files = list(annotation_path.glob("**/*.json"))

    # Prepare the "lists" folder, which is where we are going to save the split files
    lists_path = release_path / "lists"
    lists_path.mkdir(parents=True, exist_ok=True)

    # Compute sizes of each dataset partition
    dataset_size: int = len(annotation_files)
    val_size: int = int(val_percentage * dataset_size)
    test_size: int = int(test_percentage * dataset_size)
    train_size: int = dataset_size - val_size - test_size
    split_id = f"{train_size}_{val_size}_{test_size}"

    # Compute split id, a combination of val precentage, test percentage and split seed
    # The split id is used to create a folder with the same name in the "lists" folder
    if split_seed != 0:
        split_id += f"_s{split_seed}"
    split_path = lists_path / split_id

    # Build a split paths dictionary. The split paths are indexed by strategy (e.g. random
    # or stratified), and by partition (train/val/test)
    split = _build_split(split_path, stratified_types)
    assert split.is_valid()

    # Do the actual splitting
    split_path.mkdir(exist_ok=True)

    if split.random:
        _random_split(
            annotation_path=annotation_path,
            annotation_files=annotation_files,
            split=split.random,
            train_size=train_size,
            val_size=val_size,
            test_size=test_size,
            split_seed=split_seed,
        )

    if split.stratified:
        _stratified_split(
            annotation_path=annotation_path,
            split=split.stratified,
            annotation_files=annotation_files,
            train_size=train_size,
            val_size=val_size,
            test_size=test_size,
            stratified_types=stratified_types,
            split_seed=split_seed,
        )

    # Create symlink for default split
    default_split_path = lists_path / "default"
    if make_default_split or not default_split_path.exists():
        if default_split_path.exists():
            default_split_path.unlink()
        default_split_path.symlink_to(f"./{split_id}")

    return split_path


def _random_split(
    annotation_path: Path,
    annotation_files: List[Path],
    split: Dict[str, Path],
    train_size: int,
    val_size: int,
    test_size: int,
    split_seed: int,
) -> None:
    np.random.seed(split_seed)

    indices = np.random.permutation(train_size + val_size + test_size)
    train_indices = list(indices[:train_size])
    val_indices = list(indices[train_size : train_size + val_size])
    test_indices = list(indices[train_size + val_size :])

    _write_to_file(annotation_path, annotation_files, split["train"], train_indices)
    _write_to_file(annotation_path, annotation_files, split["val"], val_indices)
    _write_to_file(annotation_path, annotation_files, split["test"], test_indices)


def _stratified_split(
    annotation_path: Path,
    split: Dict[str, Dict[str, Path]],
    annotation_files: List[Path],
    train_size: int,
    val_size: int,
    test_size: int,
    stratified_types: List[str],
    split_seed: int,
) -> None:
    if len(stratified_types) == 0:
        return

    for stratified_type in stratified_types:
        _, idx_to_classes = extract_classes(annotation_path, stratified_type)
        if len(idx_to_classes) == 0:
            continue

        train_indices, val_indices, test_indices = _stratify_samples(
            idx_to_classes=idx_to_classes,
            split_seed=split_seed,
            train_size=train_size,
            val_size=val_size,
            test_size=test_size,
        )

        stratified_indices = train_indices + val_indices + test_indices
        for idx in range(train_size + val_size + test_size):
            if idx in stratified_indices:
                continue

            if len(train_indices) < train_size:
                train_indices.append(idx)
            elif len(val_indices) < val_size:
                val_indices.append(idx)
            else:
                test_indices.append(idx)

        _write_to_file(annotation_path, annotation_files, split[stratified_type]["train"], train_indices)
        _write_to_file(annotation_path, annotation_files, split[stratified_type]["val"], val_indices)
        _write_to_file(annotation_path, annotation_files, split[stratified_type]["test"], test_indices)


def _stratify_samples(
    idx_to_classes: Dict[int, Set[str]], split_seed: int, train_size: int, val_size: int, test_size: int
) -> Tuple[List[int], List[int], List[int]]:
    """Splits the list of indices into train, val and test according to their labels (stratified)

    Parameters
    ----------
    idx_to_classes: dict
    Dictionary where keys are image indices and values are all classes
    contained in that image
    split_seed : int
        Seed for the randomness
    train_size : int
        Number of training images
    val_size : int
        Number of validation images
    test_size : int
        Number of test images

    Returns
    -------
    X_train, X_val, X_test : list
        List of indices of the images for each split
    """

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

    dataset_size = train_size + val_size + test_size

    X_train, X_tmp, y_train, y_tmp = _remove_cross_contamination(
        *train_test_split(
            np.array(file_indices),
            np.array(labels),
            test_size=(val_size + test_size) / dataset_size,
            random_state=split_seed,
            stratify=labels,
        ),
        val_size + test_size,
    )

    # Append files whose support set is 1 to train
    X_train = np.concatenate((X_train, np.array(single_files)), axis=0)
    X_val, X_test, y_val, y_test = _remove_cross_contamination(
        *train_test_split(
            X_tmp,
            y_tmp,
            test_size=(test_size / (val_size + test_size)),
            random_state=split_seed,
            stratify=y_tmp,
        ),
        test_size,
    )

    # Remove duplicates within the same set
    # NOTE: doing that earlier (e.g. in _remove_cross_contamination()) would produce mathematical
    # mistakes in the class balancing between validation and test sets.
    return (list(set(X_train.astype(int))), list(set(X_val.astype(int))), list(set(X_test.astype(int))))


def _remove_cross_contamination(
    X_a: np.ndarray,
    X_b: np.ndarray,
    y_a: np.ndarray,
    y_b: np.ndarray,
    b_min_size: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
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
    for a in _unique(X_a):
        # If a not in X_b, don't remove a from anywhere
        if a not in X_b:
            continue

        # Remove a from X_b if it's large enough
        keep_locations = X_b != a
        if len(_unique(X_b[keep_locations])) >= b_min_size:
            X_b = X_b[keep_locations]
            y_b = y_b[keep_locations]
            continue

        # Remove from X_a otherwise
        keep_locations = X_a != a
        X_a = X_a[keep_locations]
        y_a = y_a[keep_locations]

    return X_a, X_b, y_a, y_b


def _unique(array: np.ndarray) -> np.ndarray:
    """Returns unique elements of numpy array, maintaining the occurrency order"""
    indexes = np.unique(array, return_index=True)[1]
    return array[sorted(indexes)]


def _write_to_file(annotation_path: Path, annotation_files: List[Path], file_path: Path, split_idx: Iterable) -> None:
    with open(str(file_path), "w") as f:
        for i in split_idx:
            # To deal with recursive search, we want to write the difference between the annotation path
            # and its parent, without the file extension
            stem = str(annotation_files[i]).replace(f"{annotation_path}/", "").split(".json")[0]
            f.write(f"{stem}\n")


def _validate_split(val_percentage: float, test_percentage: float) -> None:
    if val_percentage is None or not 0 < val_percentage < 1:
        raise ValueError(f"Invalid validation percentage ({val_percentage}). Must be a float x, where 0 < x < 1.")
    if test_percentage is None or not 0 < test_percentage < 1:
        raise ValueError(f"Invalid test percentage ({test_percentage}). Must be a float x, where 0 < x < 1.")
    if val_percentage + test_percentage >= 1:
        raise ValueError(
            f"Invalid combination of validation ({val_percentage}) and test ({test_percentage}) percentages. "
            f"Their sum must be a value x, where x < 1."
        )


def _build_split(
    split_path: Path, stratified_types: List[str], partitions: List[str] = ["train", "val", "test"]
) -> Split:
    split = Split()

    split.random = {partition: split_path / f"random_{partition}.txt" for partition in partitions}
    if len(stratified_types) == 0:
        return split

    stratified_dict: Dict[str, Dict[str, Path]] = {}
    for stratified_type in stratified_types:
        stratified_dict[stratified_type] = {
            partition: split_path / f"stratified_{stratified_type}_{partition}.txt" for partition in partitions
        }
    split.stratified = stratified_dict
    return split
