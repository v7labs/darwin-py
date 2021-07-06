from pathlib import Path
from typing import Dict, Iterable, List, Optional, Union

import numpy as np

from darwin.dataset.utils import extract_classes, get_release_path


def split_dataset(
    dataset_path: Union[Path, str],
    release_name: Optional[str] = None,
    val_percentage: float = 10,
    test_percentage: float = 20,
    split_seed: int = 0,
    make_default_split: bool = True,
    stratified_types: List[str] = ["bounding_box", "polygon", "tag"],
):
    """
    Given a local a dataset (pulled from Darwin), split it by creating lists of filenames.
    The partitions to split the dataset into are called train, val and test.

    The dataset is always split randomly, and can be additionally split according to the
    stratified strategy by providing a list of stratified types.

    Parameters
    ----------
    dataset_path : Path
        Local path to the dataset
    release_name : str
        Version of the dataset
    val_percentage : float
        Percentage of images used in the validation set
    test_percentage : float
        Percentage of images used in the test set
    split_seed : int
        Fix seed for random split creation
    make_default_split : bool
        Makes this split the default split
    stratified_types : List[str]
        List of annotation types to split with the stratified strategy

    Returns
    -------
    splits : dict
        Keys are the different splits (random, tags, ...) and values are the relative file names
    """
    # Requirements: scikit-learn
    try:
        import sklearn  # noqa
    except ImportError:
        raise ImportError(
            "Darwin requires scikit-learn to split a dataset. Install it using: pip install scikit-learn"
        ) from None

    validate_split(val_percentage, test_percentage)

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

    # Compute split id, a combination of val precentage, test percentage and split seed
    # The split id is used to create a folder with the same name in the "lists" folder
    split_id = f"split_v{int(val_percentage)}_t{int(test_percentage)}"
    if split_seed != 0:
        split_id += f"_s{split_seed}"
    split_path = lists_path / split_id

    # Build a split paths dictionary. The split paths are indexed by strategy (e.g. random
    # or stratified), and by partition (train/val/test)
    splits = build_split_paths_dict(split_path, stratified_types)

    # Do the actual splitting
    split_path.mkdir(exist_ok=True)
    random_split(annotation_path, annotation_files, splits, val_percentage, test_percentage, split_seed)
    stratified_split(
        annotation_path, splits, annotation_files, val_percentage, test_percentage, stratified_types, split_seed
    )

    # Create symlink for default split
    split = lists_path / "default"
    if make_default_split or not split.exists():
        if split.exists():
            split.unlink()
        split.symlink_to(f"./{split_id}")

    return split_path


def validate_split(val_percentage: float, test_percentage: float):
    if val_percentage is None or not 0 <= val_percentage < 100:
        raise ValueError(f"Invalid validation percentage ({val_percentage}). " f"Must be >= 0 and < 100")
    if test_percentage is None or not 0 <= test_percentage < 100:
        raise ValueError(f"Invalid test percentage ({test_percentage}). " f"Must be >= 0 and < 100")
    if not 1 <= val_percentage + test_percentage < 100:
        raise ValueError(
            f"Invalid combination of validation ({val_percentage}) "
            f"and test ({test_percentage}) percentages. Their sum must be > 1 and < 100"
        )


def build_split_paths_dict(split_path: Path, stratified_types: List[str]) -> Dict[str, Dict[str, Path]]:
    splits = {
        "random": {
            "train": split_path / "random_train.txt",
            "val": split_path / "random_val.txt",
            "test": split_path / "random_test.txt",
        },
    }

    if len(stratified_types) == 0:
        return splits

    splits["stratified"] = {}
    for stratified_type in stratified_types:
        splits["stratified"][stratified_type] = {
            "train": split_path / f"stratified_{stratified_type}_train.txt",
            "val": split_path / f"stratified_{stratified_type}_val.txt",
            "test": split_path / f"stratified_{stratified_type}_test.txt",
        }

    return splits


def random_split(
    annotation_path: Path,
    annotation_files: List[Path],
    splits: Dict[str, Dict[str, Path]],
    val_percentage: float,
    test_percentage: float,
    split_seed: int,
):
    # Compute split sizes
    dataset_size = sum(1 for _ in annotation_files)
    val_size = int(dataset_size * (val_percentage / 100.0))
    test_size = int(dataset_size * (test_percentage / 100.0))
    train_size = dataset_size - val_size - test_size

    # Slice a permuted array as big as the dataset
    np.random.seed(split_seed)
    indices = np.random.permutation(dataset_size)
    train_indices = list(indices[:train_size])
    val_indices = list(indices[train_size : train_size + val_size])
    test_indices = list(indices[train_size + val_size :])

    write_to_file(annotation_path, annotation_files, splits["random"]["train"], train_indices)
    write_to_file(annotation_path, annotation_files, splits["random"]["val"], val_indices)
    write_to_file(annotation_path, annotation_files, splits["random"]["test"], test_indices)


def stratified_split(
    annotation_path: Path,
    splits: Dict[str, Dict[str, Path]],
    annotation_files: List[Path],
    val_percentage: float,
    test_percentage: float,
    stratified_types: List[str],
    split_seed: int,
):
    if len(stratified_types) == 0:
        return

    for stratified_type in stratified_types:
        _, idx_to_classes = extract_classes(annotation_path, stratified_type)
        if len(idx_to_classes) == 0:
            continue

        dataset_size = sum(1 for _ in annotation_files)
        val_size = int(dataset_size * (val_percentage / 100.0))
        test_size = int(dataset_size * (test_percentage / 100.0))
        train_size = dataset_size - val_size - test_size

        train_indices, val_indices, test_indices = _stratify_samples(
            idx_to_classes, split_seed, test_percentage, val_percentage, test_size, val_size
        )

        stratified_indices = train_indices + val_indices + test_indices
        for idx in range(dataset_size):
            if idx in stratified_indices:
                continue

            if len(train_indices) < train_size:
                train_indices.append(idx)
            elif len(val_indices) < val_size:
                val_indices.append(idx)
            else:
                test_indices.append(idx)

        write_to_file(annotation_path, annotation_files, splits["stratified"][stratified_type]["train"], train_indices)
        write_to_file(annotation_path, annotation_files, splits["stratified"][stratified_type]["val"], val_indices)
        write_to_file(annotation_path, annotation_files, splits["stratified"][stratified_type]["test"], test_indices)


def _stratify_samples(idx_to_classes, split_seed, test_percentage, val_percentage, test_size, val_size):
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
    test_size : int
        Number of test images
    val_size : int
        Number of validation images


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

    X_train, X_tmp, y_train, y_tmp = remove_cross_contamination(
        *train_test_split(
            np.array(file_indices),
            np.array(labels),
            test_size=(val_percentage + test_percentage) / 100.0,
            random_state=split_seed,
            stratify=labels,
        ),
        val_size + test_size,
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
        ),
        test_size,
    )

    # Remove duplicates within the same set
    # NOTE: doing that earlier (e.g. in remove_cross_contamination()) would produce mathematical
    # mistakes in the class balancing between validation and test sets.
    return (list(set(X_train.astype(np.int))), list(set(X_val.astype(np.int))), list(set(X_test.astype(np.int))))


def remove_cross_contamination(X_a: np.ndarray, X_b: np.ndarray, y_a: np.ndarray, y_b: np.ndarray, b_min_size: int):
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
    for a in unique(X_a):
        # If a not in X_b, don't remove a from anywhere
        if a not in X_b:
            continue

        # Remove a from X_b if it's large enough
        keep_locations = X_b != a
        if len(unique(X_b[keep_locations])) >= b_min_size:
            X_b = X_b[keep_locations]
            y_b = y_b[keep_locations]
            continue

        # Remove from X_a otherwise
        keep_locations = X_a != a
        X_a = X_a[keep_locations]
        y_a = y_a[keep_locations]

    return X_a, X_b, y_a, y_b


def unique(array):
    """Returns unique elements of numpy array, maintaining the occurrency order"""
    indexes = np.unique(array, return_index=True)[1]
    return array[sorted(indexes)]


def write_to_file(annotation_path: Path, annotation_files: List[Path], file_path: Path, split_idx: Iterable):
    with open(str(file_path), "w") as f:
        for i in split_idx:
            # To deal with recursive search, we want to write the difference between the annotation path
            # and its parent, without the file extension
            stem = str(annotation_files[i]).replace(f"{annotation_path}/", "").split(".json")[0]
            f.write(f"{stem}\n")
