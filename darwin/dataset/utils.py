import json
import os
from collections import defaultdict
from pathlib import Path
from typing import List, Optional, Iterable
from sklearn.model_selection import train_test_split

import numpy as np

def extract_classes(annotation_files: List, annotation_type: str):
    """
    Given a the GT as json files extracts all classes and an maps images index to classes

    Parameters
    ----------
    annotation_files: list
        List of json files with the GT information of each image
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
    classes = defaultdict(set)
    indices_to_classes = defaultdict(set)
    for i, file_name in enumerate(annotation_files):
        with open(file_name) as f:
            for annotation in json.load(f)["annotations"]:
                if annotation_type not in annotation:
                    continue
                class_name = annotation["name"]
                indices_to_classes[i].add(class_name)
                classes[class_name].add(i)
    return classes, indices_to_classes

def make_class_list(
        file_name: str,
        annotation_files: List,
        lists_path: Path,
        annotation_type: str,
        force_resplit: Optional[bool] = False,
        add_background: Optional[bool] = False
):
    """
    Support function to extract classes and save the output to file

    Parameters
    ----------
    file_name : str
        Name of the file where to store the results
    annotation_files : list
        List of json files with the GT information of each image
    lists_path : Path
        Path to the lists folder
    annotation_type : str
        Type of annotations to use, e.g. 'tag' or 'polygon'
    force_resplit : bool
        Force the creation of the output file, should the list already exist
    add_background : bool
        Add the '__background__' class to the list of classes

    Returns
    -------
    idx_to_classes: dict
    Dictionary where keys are image indices and values are all classes
    contained in that image
    """
    fname = lists_path / file_name
    if not fname.exists() or force_resplit:
        classes, idx_to_classes = extract_classes(annotation_files, annotation_type=annotation_type)
        classes_names = list(classes.keys())
        if add_background:
            classes_names.insert(0, "__background__")
        with open(str(fname), "w") as f:
            for c in classes_names:
                f.write(f"{c}\n")
        return idx_to_classes

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
    # Expand the list of files with all the classes
    expanded_list = [(k, c) for k, v in idx_to_classes.items() for c in v]
    # Stratify
    file_indices, labels = zip(*expanded_list)
    X_train, X_tmp, y_train, y_tmp = remove_cross_contamination(
        *train_test_split(np.array(file_indices), np.array(labels),
                          test_size=val_percentage + test_percentage,
                          random_state=split_seed,
                          stratify=labels)
    )
    X_val, X_test, y_val, y_test = remove_cross_contamination(
        *train_test_split(X_tmp, y_tmp,
                          test_size=test_percentage / (val_percentage + test_percentage),
                          random_state=split_seed,
                          stratify=y_tmp)
    )
    # Remove duplicates within the same set
    # NOTE: doing that earlier (e.g. in remove_cross_contamination()) would produce mathematical
    # mistakes in the class balancing between validation and test sets.
    return list(set(X_train)), list(set(X_val)), list(set(X_test))

def split_dataset(
        root: Path,
        val_percentage: Optional[float] = 0.1,
        test_percentage: Optional[float] = 0.2,
        force_resplit: Optional[bool] = False,
        split_seed: Optional[int] = 42,
):
    """
    Given a local a dataset (pulled from Darwin) creates lists of file names
    for each split for train, validation, and test.

    Parameters
    ----------
    root : Path
        Path of the dataset on the file system
    val_percentage : float
        Percentage of images used in the validation set
    test_percentage : float
        Percentage of images used in the test set
    force_resplit : bool
        Discard previous split and create a new one
    split_seed : in
        Fix seed for random split creation

    Returns
    -------
    split_path : Path
        Local path to the split folder
    splits : dict
        Keys are the different splits (random, tags, ...) and values are the relative file names
    """
    assert root.exists()
    annotation_path = Path(root / "annotations")
    assert annotation_path.exists()
    annotation_files = list(annotation_path.glob("*.json"))

    # Extract list of classes and create respective files
    lists_path = root / "lists"
    lists_path.mkdir(parents=True, exist_ok=True)
    idx_to_classes_polygon = make_class_list(
        "classes_polygon.txt", annotation_files, lists_path, "polygon", force_resplit, add_background=True
    )
    idx_to_classes_tags = make_class_list(
        "classes_tags.txt", annotation_files, lists_path, "tag", force_resplit
    )

    # Create split id, path and final split paths
    assert val_percentage is not None
    assert test_percentage is not None
    assert split_seed is not None
    assert 0 < val_percentage < 1.0
    assert 0 <= test_percentage < 1.0
    assert val_percentage + test_percentage < 1.0
    split_id = f'split_v{int(val_percentage*100)}_t{int(test_percentage*100)}_s{split_seed}'
    split_path = lists_path / split_id

    splits = {}
    # Do the actual split
    if not split_path.exists() or force_resplit:
        os.makedirs(str(split_path), exist_ok=True)

        # RANDOM SPLIT
        train_path = Path(split_path / "random_split_train.txt")
        val_path = Path(split_path / "random_split_val.txt")
        test_path = Path(split_path / "random_split_test.txt")
        splits['random'] = {'train': train_path, 'val':val_path, 'test':test_path}
        # Compute split sizes
        dataset_size = sum(1 for _ in annotation_files)
        val_size = int(dataset_size * val_percentage)
        test_size = int(dataset_size * test_percentage)
        train_size = dataset_size - val_size - test_size
        # Slice a permuted array as big as the dataset
        np.random.seed(split_seed)
        indices = np.random.permutation(dataset_size)
        train_indices = indices[:train_size]
        val_indices = indices[train_size : train_size + val_size]
        test_indices = indices[train_size + val_size :]
        # Write files
        _write_to_file(annotation_files, train_path, train_indices)
        _write_to_file(annotation_files, val_path, val_indices)
        _write_to_file(annotation_files, test_path, test_indices)

        # STRATIFIED SPLIT ON POLYGONS
        train_path = Path(split_path / "stratified_polygon_train.txt")
        val_path = Path(split_path / "stratified_polygon_split_val.txt")
        test_path = Path(split_path / "stratified_polygon_test.txt")
        splits['polygon'] = {'train': train_path, 'val': val_path, 'test': test_path}
        # Stratify
        train_indices, val_indices, test_indices = _stratify_samples(
            idx_to_classes_polygon, split_seed, test_percentage, val_percentage
        )
        # Write files
        _write_to_file(annotation_files, train_path, train_indices)
        _write_to_file(annotation_files, val_path, val_indices)
        _write_to_file(annotation_files, test_path, test_indices)

        # STRATIFIED SPLIT ON TAGS
        train_path = Path(split_path / "stratified_tags_train.txt")
        val_path = Path(split_path / "stratified_tags_val.txt")
        test_path = Path(split_path / "stratified_tags_test.txt")
        splits['tags'] = {'train': train_path, 'val': val_path, 'test': test_path}
        # Stratify
        train_indices, val_indices, test_indices = _stratify_samples(
            idx_to_classes_tags, split_seed, test_percentage, val_percentage
        )
        # Write files
        _write_to_file(annotation_files, train_path, train_indices)
        _write_to_file(annotation_files, val_path, val_indices)
        _write_to_file(annotation_files, test_path, test_indices)

    return split_path, splits

