from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

if TYPE_CHECKING:
    from darwin.client import Client
    from darwin.dataset import RemoteDataset

from concurrent.futures import ThreadPoolExecutor
from itertools import chain

import darwin.datatypes as dt
from darwin.datatypes import PathLike
from darwin.utils import secure_continue_request
from rich.progress import track


def build_main_annotations_lookup_table(annotation_classes: List[Dict[str, Any]]) -> Dict[str, Any]:
    MAIN_ANNOTATION_TYPES = [
        "bounding_box",
        "cuboid",
        "ellipse",
        "keypoint",
        "line",
        "link",
        "polygon",
        "skeleton",
        "tag",
    ]
    lookup: Dict[str, Any] = {}
    for cls in annotation_classes:
        for annotation_type in cls["annotation_types"]:
            if annotation_type in MAIN_ANNOTATION_TYPES:
                if annotation_type not in lookup:
                    lookup[annotation_type] = {}
                lookup[annotation_type][cls["name"]] = cls["id"]

    return lookup


def find_and_parse(
    importer: Callable[[Path], Union[List[dt.AnnotationFile], dt.AnnotationFile, None]], file_paths: List[PathLike]
) -> Optional[Iterable[dt.AnnotationFile]]:
    # TODO: this could be done in parallel
    for file_path in map(Path, file_paths):
        files = file_path.glob("**/*") if file_path.is_dir() else [file_path]
        for f in files:
            # importer returns either None, 1 annotation file or a list of annotation files
            parsed_files: Union[List[dt.AnnotationFile], dt.AnnotationFile, None] = importer(f)
            if parsed_files is None:
                continue

            if type(parsed_files) is not list:
                parsed_files = [parsed_files]

            for parsed_file in parsed_files:
                # clear to save memory
                parsed_file.annotations = []
                yield parsed_file


def build_attribute_lookup(dataset: "RemoteDataset") -> Dict[str, Any]:
    attributes: Any = dataset.fetch_remote_attributes()
    lookup: Dict[str, Any] = {}
    for attribute in attributes:
        class_id = attribute["class_id"]
        if class_id not in lookup:
            lookup[class_id] = {}
        lookup[class_id][attribute["name"]] = attribute["id"]
    return lookup


def get_remote_files(dataset: "RemoteDataset", filenames: List[str]) -> Dict[str, int]:
    """Fetches remote files from the datasets, in chunks of 100 filesnames at a time"""
    remote_files = {}
    for i in range(0, len(filenames), 100):
        chunk = filenames[i : i + 100]
        for remote_file in dataset.fetch_remote_files(
            {"types": "image,playback_video,video_frame", "filenames": ",".join(chunk)}
        ):
            remote_files[remote_file.full_path] = remote_file.id
    return remote_files


def _resolve_annotation_classes(
    local_annotation_classes: List[dt.AnnotationClass],
    classes_in_dataset: Dict[str, Any],
    classes_in_team: Dict[str, Any],
) -> Tuple[Set[dt.AnnotationClass], Set[dt.AnnotationClass]]:
    local_classes_not_in_dataset: Set[dt.AnnotationClass] = set()
    local_classes_not_in_team: Set[dt.AnnotationClass] = set()

    for local_cls in local_annotation_classes:
        local_annotation_type = local_cls.annotation_internal_type or local_cls.annotation_type
        # Only add the new class if it doesn't exist remotely already
        if local_annotation_type in classes_in_dataset and local_cls.name in classes_in_dataset[local_annotation_type]:
            continue

        # Only add the new class if it's not included in the list of the missing classes already
        if local_cls.name in [missing_class.name for missing_class in local_classes_not_in_dataset]:
            continue
        if local_cls.name in [missing_class.name for missing_class in local_classes_not_in_team]:
            continue

        if local_annotation_type in classes_in_team and local_cls.name in classes_in_team[local_annotation_type]:
            local_classes_not_in_dataset.add(local_cls)
        else:
            local_classes_not_in_team.add(local_cls)

    return local_classes_not_in_dataset, local_classes_not_in_team


def import_annotations(
    dataset: "RemoteDataset",
    importer: Callable[[Path], Union[List[dt.AnnotationFile], dt.AnnotationFile, None]],
    file_paths: List[PathLike],
    append: bool,
    max_workers: int = 4,
    require_user_confirm: bool = False,
) -> None:
    """
    Imports the given given Annotations into the given Dataset.

    Parameters
    ----------
    dataset : RemoteDataset
        Dataset where the Annotations will be imported to.
    importer : Callable[[Path], Union[List[dt.AnnotationFile], dt.AnnotationFile, None]]
        Parsing module containing the logic to parse the given Annotation files given in
        `files_path`. See `importer/format` for a list of out of supported parsers.
    file_paths : List[PathLike]
        A list of `Path`'s or strings containing the Annotations we wish to import.
    append : bool
        If `True` appends the given annotations to the datasets. If `False` will override them.
    max_workers: Optional[int]
        The number of workers to be used when uploading the annnotations. Defaults to 4

    Returns
    -------
        None

    Raises
    -------
    ValueError
        If file_paths is not a list.
    """
    if not isinstance(file_paths, list):
        raise ValueError(f"file_paths must be a list of 'Path' or 'str'. Current value: {file_paths}")
    # we need to fetch all the remote classes in order to find the correct id
    print("Fetching remote class list...")
    team_classes: List[Dict[str, Any]] = dataset.fetch_remote_classes(team_wide=True)
    if not team_classes:
        raise ValueError("Unable to fetch remote class list.")

    # team-wide classes belonging to our dataset
    classes_in_dataset: Dict[str, Any] = build_main_annotations_lookup_table(
        [cls for cls in team_classes if cls["available"]]
    )
    # team-wide classes not yet belonging to any dataset
    classes_in_team: Dict[str, Any] = build_main_annotations_lookup_table(
        [cls for cls in team_classes if not cls["available"]]
    )
    # attributes are sub annotations and need a different look-up table
    attributes = build_attribute_lookup(dataset)
    # we need to find and parse the specified files in `file_paths`
    print("Retrieving local annotations ...")
    parsed_files: List[dt.AnnotationFile] = list(find_and_parse(importer, file_paths))
    # filenames are the images' names
    filenames: List[str] = [parsed_file.filename for parsed_file in parsed_files]
    print("Fetching remote file list...")
    # This call will only filter by filename; so can return a superset of matched files across different paths
    # There is logic in this function to then include paths to narrow down to the single correct matching file
    remote_path_to_item_id = get_remote_files(dataset, filenames)
    local_files = []
    local_files_missing_remotely = []
    for parsed_file in parsed_files:
        if parsed_file.full_path not in remote_path_to_item_id:
            local_files_missing_remotely.append(parsed_file)
        else:
            local_files.append(parsed_file)
    # now we have a list of missing files (images) that we have locally but not in the remote
    # and a list of all the files we have both locally and in the remote
    print(f"{len(local_files) + len(local_files_missing_remotely)} annotation file(s) found.")
    missing_files_remotely: bool = len(local_files_missing_remotely) > 0
    if missing_files_remotely:
        print(f"{len(local_files_missing_remotely)} file(s) are missing from the dataset")
        for local_file in local_files_missing_remotely:
            print(f"\t{local_file.path}: '{local_file.full_path}'")

        if not require_user_confirm:
            # ask the user if he wants to import the annotations
            if not secure_continue_request():
                # if user doesn't confirm, we exit the function
                return None
    # using the look-up defined before, we find out the classes that are not in the dataset and not in the team
    local_classes_not_in_dataset, local_classes_not_in_team = _resolve_annotation_classes(
        [annotation_class for file in local_files for annotation_class in file.annotation_classes],
        classes_in_dataset,
        classes_in_team,
    )

    print(f"{len(local_classes_not_in_team)} classes needs to be created.")
    print(f"{len(local_classes_not_in_dataset)} classes needs to be added to {dataset.identifier}")
    # if we have skeletons, we need to have a specified class for each one of them
    missing_skeletons: List[dt.AnnotationClass] = list(filter(_is_skeleton_class, local_classes_not_in_team))
    missing_skeleton_names: str = ", ".join(map(_get_skeleton_name, missing_skeletons))
    if missing_skeletons:
        print(
            f"Found missing skeleton classes: {missing_skeleton_names}. Missing Skeleton classes cannot be created. Exiting now."
        )
        return None

    if local_classes_not_in_team:
        print("About to create the following classes")
        for missing_class in local_classes_not_in_team:
            print(
                f"\t{missing_class.name}, type: {missing_class.annotation_internal_type or missing_class.annotation_type}"
            )
        if not require_user_confirm:
            if not secure_continue_request():
                return None
        for missing_class in local_classes_not_in_team:
            dataset.create_annotation_class(
                missing_class.name, missing_class.annotation_internal_type or missing_class.annotation_type
            )
    if local_classes_not_in_dataset:
        print(f"About to add the following classes to {dataset.identifier}")
        for cls in local_classes_not_in_dataset:
            dataset.add_annotation_class(cls)

    # Refetch classes to update mappings
    if local_classes_not_in_team or local_classes_not_in_dataset:
        maybe_remote_classes: List[Dict[str, Any]] = dataset.fetch_remote_classes()
        if not maybe_remote_classes:
            raise ValueError("Unable to fetch remote classes.")

        remote_classes = build_main_annotations_lookup_table(maybe_remote_classes)
    else:
        remote_classes = build_main_annotations_lookup_table(team_classes)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        missing_files_paths: List[Path] = [missing_file.full_path for missing_file in local_files_missing_remotely]

        def get_uplodable_files(local_path: Path) -> List[dt.AnnotationFile]:
            parsed_files = importer(local_path)
            if type(parsed_files) is not list:
                parsed_files = [parsed_files]
            # remove files missing on the server
            uploadable_files = [
                parsed_file for parsed_file in parsed_files if parsed_file.full_path not in missing_files_paths
            ]
            return uploadable_files

        def import_annotation_from_annotation_file(parsed_file: dt.AnnotationFile):
            item_id = remote_path_to_item_id[parsed_file.full_path]
            _import_annotations(
                dataset.client, item_id, remote_classes, attributes, parsed_file.annotations, dataset, append,
            )

        print(f"Uploading annotations with {max_workers} workers")
        # let's get the file paths we need
        paths: Set[Path] = set(local_file.path for local_file in local_files)
        # create our multi threading stage to get the files we need to import
        uploadable_files: List[List[dt.AnnotationFile]] = list(executor.map(get_uplodable_files, paths))
        # parsed_files is a list of lists, we need to flat it
        # we also convert it to list because we need to know its len
        parsed_files_flat: List[dt.AnnotationFile] = list(chain.from_iterable(uploadable_files))
        # create our multi threading stage to import the annotations
        import_annotation_stage: Iterator = track(
            executor.map(import_annotation_from_annotation_file, parsed_files_flat), total=len(parsed_files_flat)
        )
        # resolve the stage
        list(import_annotation_stage)


def _is_skeleton_class(the_class: dt.AnnotationClass) -> bool:
    return (the_class.annotation_internal_type or the_class.annotation_type) == "skeleton"


def _get_skeleton_name(skeleton: dt.AnnotationClass) -> str:
    return skeleton.name


def _handle_subs(
    annotation: dt.Annotation, data: Dict[str, Any], annotation_class_id: str, attributes: Dict[str, Any]
) -> Dict[str, Any]:
    for sub in annotation.subs:
        if sub.annotation_type == "text":
            data["text"] = {"text": sub.data}
        elif sub.annotation_type == "attributes":
            data["attributes"] = {
                "attributes": [
                    attributes[annotation_class_id][attr]
                    for attr in sub.data
                    if annotation_class_id in attributes and attr in attributes[annotation_class_id]
                ]
            }
        elif sub.annotation_type == "instance_id":
            data["instance_id"] = {"value": sub.data}
        else:
            data[sub.annotation_type] = sub.data
    return data


def _handle_complex_polygon(annotation: dt.Annotation, data: Dict[str, Any]) -> Dict[str, Any]:
    if "complex_polygon" in data:
        del data["complex_polygon"]
        data["polygon"] = {"path": annotation.data["paths"][0], "additional_paths": annotation.data["paths"][1:]}
    return data


def _import_annotations(
    client: "Client",
    id: int,
    remote_classes: Dict[str, Any],
    attributes: Dict[str, Any],
    annotations: List[dt.Annotation],
    dataset: "RemoteDataset",
    append: bool,
):
    serialized_annotations = []
    for annotation in annotations:
        annotation_class = annotation.annotation_class
        annotation_type = annotation_class.annotation_internal_type or annotation_class.annotation_type
        annotation_class_id = remote_classes[annotation_type][annotation_class.name]

        if isinstance(annotation, dt.VideoAnnotation):
            data = annotation.get_data(
                only_keyframes=True,
                post_processing=lambda annotation, data: _handle_subs(
                    annotation, _handle_complex_polygon(annotation, data), annotation_class_id, attributes
                ),
            )
        else:
            data = {annotation_class.annotation_type: annotation.data}
            data = _handle_complex_polygon(annotation, data)
            data = _handle_subs(annotation, data, annotation_class_id, attributes)

        serialized_annotations.append({"annotation_class_id": annotation_class_id, "data": data})

    payload: Dict[str, Any] = {"annotations": serialized_annotations}
    if append:
        payload["overwrite"] = "false"

    try:
        client.import_annotation_class(id, payload=payload)
    except:
        print(f"warning, failed to upload annotation to item {id}. Annotations: {payload}")
