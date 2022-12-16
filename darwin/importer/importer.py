from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

if TYPE_CHECKING:
    from darwin.client import Client
    from darwin.dataset import RemoteDataset

import deprecation
from rich.console import Console
from rich.progress import track
from rich.theme import Theme

import darwin.datatypes as dt
from darwin.datatypes import PathLike
from darwin.exceptions import IncompatibleOptions, RequestEntitySizeExceeded
from darwin.utils import secure_continue_request
from darwin.version import __version__

# Classes missing import support on backend side
UNSUPPORTED_CLASSES = ["string", "graph"]

DEPRECATION_MESSAGE = """

This function is going to be turned into private. This means that breaking 
changes in its interface and implementation are to be expected. We encourage using ``import_annotations`` 
instead of calling this low-level function directly.

"""


@deprecation.deprecated(
    deprecated_in="0.7.12",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
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
        "string",
        "table",
        "graph",
    ]
    lookup: Dict[str, Any] = {}
    for cls in annotation_classes:
        for annotation_type in cls["annotation_types"]:
            if annotation_type in MAIN_ANNOTATION_TYPES:
                if annotation_type not in lookup:
                    lookup[annotation_type] = {}
                lookup[annotation_type][cls["name"]] = cls["id"]

    return lookup


@deprecation.deprecated(
    deprecated_in="0.7.12",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
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


@deprecation.deprecated(
    deprecated_in="0.7.12",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_attribute_lookup(dataset: "RemoteDataset") -> Dict[str, Any]:
    attributes: Any = dataset.fetch_remote_attributes()
    lookup: Dict[str, Any] = {}
    for attribute in attributes:
        class_id = attribute["class_id"]
        if class_id not in lookup:
            lookup[class_id] = {}
        lookup[class_id][attribute["name"]] = attribute["id"]
    return lookup


@deprecation.deprecated(
    deprecated_in="0.7.12",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def get_remote_files(dataset: "RemoteDataset", filenames: List[str], chunk_size: int() = 100) -> Dict[str, Tuple[int, str]]:
    """
    Fetches remote files from the datasets in chunks; by default 100 filenames at a time.

    The output is a two-element tuple of:
    - file ID
    - the name of the first slot for V2 items, or '0' for V1 items

    Fetching slot name is necessary here to avoid double-trip to Api downstream for remote files.
    """
    remote_files = {}
    for i in range(0, len(filenames), chunk_size):
        chunk = filenames[i : i + chunk_size]
        for remote_file in dataset.fetch_remote_files(
            {"types": "image,playback_video,video_frame", "filenames": chunk}
        ):
            slot_name = _get_slot_name(remote_file)
            remote_files[remote_file.full_path] = (remote_file.id, slot_name)
    return remote_files

def _get_slot_name(remote_file) -> str:
    slot = next(iter(remote_file.slots), {"slot_name": "0"})
    if slot:
        return slot["slot_name"]
    else:
        return "0"

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
    class_prompt: bool = True,
    delete_for_empty: bool = False,
) -> None:
    """
    Imports the given given Annotations into the given Dataset.

    Parameters
    ----------
    dataset : RemoteDataset
        Dataset where the Annotations will be imported to.
    importer : Callable[[Path], Union[List[dt.AnnotationFile], dt.AnnotationFile, None]]
        Parsing module containing the logic to parse the given Annotation files given in
        ``files_path``. See ``importer/format`` for a list of out of supported parsers.
    file_paths : List[PathLike]
        A list of ``Path``'s or strings containing the Annotations we wish to import.
    append : bool
        If ``True`` appends the given annotations to the datasets. If ``False`` will override them.
        Incompatible with ``delete-for-empty``.
    class_prompt : bool
        If ``False`` classes will be created and added to the datasets without requiring a user's prompt.
    delete_for_empty : bool, default: False
        If ``True`` will use empty annotation files to delete all annotations from the remote file.
        If ``False``, empty annotation files will simply be skipped.
        Only works for V2 datasets.
        Incompatible with ``append``.

    Raises
    -------
    ValueError

        - If ``file_paths`` is not a list.
        - If the application is unable to fetch any remote classes.
        - If the application was unable to find/parse any annotation files.
        - If the application was unable to fetch remote file list.

    IncompatibleOptions

        - If both ``append`` and ``delete_for_empty`` are specified as ``True``.
    """
    console = Console(theme=_console_theme())

    if append and delete_for_empty:
        raise IncompatibleOptions(
            "The options 'append' and 'delete_for_empty' cannot be used together. Use only one of them."
        )

    if not isinstance(file_paths, list):
        raise ValueError(f"file_paths must be a list of 'Path' or 'str'. Current value: {file_paths}")

    console.print("Fetching remote class list...", style="info")
    team_classes: List[Dict[str, Any]] = dataset.fetch_remote_classes(True)
    if not team_classes:
        raise ValueError("Unable to fetch remote class list.")

    if delete_for_empty and dataset.version == 1:
        console.print(
            f"The '--delete-for-empty' flag only works for V2 datasets. '{dataset.name}' is a V1 dataset. Ignoring flag.",
            style="warning",
        )

    classes_in_dataset: Dict[str, Any] = build_main_annotations_lookup_table(
        [cls for cls in team_classes if cls["available"]]
    )
    classes_in_team: Dict[str, Any] = build_main_annotations_lookup_table(
        [cls for cls in team_classes if not cls["available"]]
    )
    attributes = build_attribute_lookup(dataset)

    console.print("Retrieving local annotations ...", style="info")
    local_files = []
    local_files_missing_remotely = []
    maybe_parsed_files: Optional[Iterable[dt.AnnotationFile]] = find_and_parse(importer, file_paths)
    if not maybe_parsed_files:
        raise ValueError("Not able to parse any files.")

    parsed_files = list(maybe_parsed_files)
    filenames: List[str] = [parsed_file.filename for parsed_file in parsed_files]

    console.print("Fetching remote file list...", style="info")
    # This call will only filter by filename; so can return a superset of matched files across different paths
    # There is logic in this function to then include paths to narrow down to the single correct matching file
    remote_files = []

    # Try to fetch files in large chunks; in case the filenames are too large and exceed the url size
    # retry in smaller chunks
    chunk_size = 100
    while chunk_size > 0:
        try:
            remote_files = get_remote_files(dataset, filenames, chunk_size)
            break
        except RequestEntitySizeExceeded as e:
            chunk_size -= 8
            if chunk_size <= 0:
                raise ValueError("Unable to fetch remote file list.")


    for parsed_file in parsed_files:
        if parsed_file.full_path not in remote_files:
            local_files_missing_remotely.append(parsed_file)
        else:
            local_files.append(parsed_file)

    console.print(f"{len(local_files) + len(local_files_missing_remotely)} annotation file(s) found.", style="info")
    if local_files_missing_remotely:
        console.print(f"{len(local_files_missing_remotely)} file(s) are missing from the dataset", style="warning")
        for local_file in local_files_missing_remotely:
            console.print(f"\t{local_file.path}: '{local_file.full_path}'", style="warning")

        if class_prompt and not secure_continue_request():
            return

    local_classes_not_in_dataset, local_classes_not_in_team = _resolve_annotation_classes(
        [annotation_class for file in local_files for annotation_class in file.annotation_classes],
        classes_in_dataset,
        classes_in_team,
    )

    console.print(f"{len(local_classes_not_in_team)} classes needs to be created.", style="info")
    console.print(
        f"{len(local_classes_not_in_dataset)} classes needs to be added to {dataset.identifier}", style="info"
    )

    missing_skeletons: List[dt.AnnotationClass] = list(filter(_is_skeleton_class, local_classes_not_in_team))
    missing_skeleton_names: str = ", ".join(map(_get_skeleton_name, missing_skeletons))
    if missing_skeletons:
        console.print(
            f"Found missing skeleton classes: {missing_skeleton_names}. Missing Skeleton classes cannot be created. Exiting now.",
            style="error",
        )
        return

    if local_classes_not_in_team:
        console.print("About to create the following classes", style="info")
        for missing_class in local_classes_not_in_team:
            console.print(
                f"\t{missing_class.name}, type: {missing_class.annotation_internal_type or missing_class.annotation_type}",
                style="info",
            )
        if class_prompt and not secure_continue_request():
            return
        for missing_class in local_classes_not_in_team:
            dataset.create_annotation_class(
                missing_class.name, missing_class.annotation_internal_type or missing_class.annotation_type
            )
    if local_classes_not_in_dataset:
        console.print(f"About to add the following classes to {dataset.identifier}", style="info")
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

    if dataset.version == 1:
        console.print("Importing annotations...\nEmpty annotations will be skipped.", style="info")
    elif dataset.version == 2 and delete_for_empty:
        console.print(
            "Importing annotations...\nEmpty annotation file(s) will clear all existing annotations in matching remote files.",
            style="info",
        )
    else:
        console.print(
            "Importing annotations...\nEmpty annotations will be skipped, if you want to delete annotations rerun with '--delete-for-empty'.",
            style="info",
        )

    # Need to re parse the files since we didn't save the annotations in memory
    for local_path in set(local_file.path for local_file in local_files):

        imported_files: Union[List[dt.AnnotationFile], dt.AnnotationFile, None] = importer(local_path)
        if imported_files is None:
            parsed_files = []
        elif not isinstance(imported_files, List):
            parsed_files = [imported_files]
        else:
            parsed_files = imported_files

        # remove files missing on the server
        missing_files = [missing_file.full_path for missing_file in local_files_missing_remotely]
        parsed_files = [parsed_file for parsed_file in parsed_files if parsed_file.full_path not in missing_files]

        files_to_not_track = [
            file_to_track
            for file_to_track in parsed_files
            if not file_to_track.annotations and (not delete_for_empty or dataset.version == 1)
        ]

        for file in files_to_not_track:
            console.print(f"{file.filename} has no annotations. Skipping upload...", style="warning")

        files_to_track = [file for file in parsed_files if file not in files_to_not_track]
        if files_to_track:
            _warn_unsupported_annotations(files_to_track)
            for parsed_file in track(files_to_track):
                image_id, default_slot_name = remote_files[parsed_file.full_path]

                _import_annotations(
                    dataset.client,
                    image_id,
                    remote_classes,
                    attributes,
                    parsed_file.annotations,
                    default_slot_name,
                    dataset,
                    append,
                    delete_for_empty,
                )


def _warn_unsupported_annotations(parsed_files):
    console = Console(theme=_console_theme())
    for parsed_file in parsed_files:
        skipped_annotations = []
        for annotation in parsed_file.annotations:
            if annotation.annotation_class.annotation_type in UNSUPPORTED_CLASSES:
                skipped_annotations.append(annotation)
        if len(skipped_annotations) > 0:
            types = set(map(lambda c: c.annotation_class.annotation_type, skipped_annotations))
            console.print(
                f"Import of annotation class types '{', '.join(types)}' is not yet supported. Skipping {len(skipped_annotations)} annotations from '{parsed_file.full_path}'.\n",
                style="warning",
            )


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
            attributes_with_key = []
            for attr in sub.data:
                if annotation_class_id in attributes and attr in attributes[annotation_class_id]:
                    attributes_with_key.append(attributes[annotation_class_id][attr])
                else:
                    print(f"The attribute '{attr}' for class '{annotation.annotation_class.name}' was not imported.")

            data["attributes"] = {"attributes": attributes_with_key}
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
    id: Union[str, int],
    remote_classes: Dict[str, Any],
    attributes: Dict[str, Any],
    annotations: List[dt.Annotation],
    default_slot_name: str,
    dataset: "RemoteDataset",
    append: bool,
    delete_for_empty: bool,
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

        # Insert the default slot name if not available in the import source
        if not annotation.slot_names and dataset.version > 1:
            annotation.slot_names.extend([default_slot_name])

        serialized_annotations.append(
            {
                "annotation_class_id": annotation_class_id,
                "data": data,
                "context_keys": {"slot_names": annotation.slot_names},
            }
        )

    payload: Dict[str, Any] = {"annotations": serialized_annotations}
    if append:
        payload["overwrite"] = "false"
    else:
        payload["overwrite"] = "true"

    dataset.import_annotation(id, payload=payload)


def _console_theme() -> Theme:
    return Theme(
        {"success": "bold green", "warning": "bold yellow", "error": "bold red", "info": "bold deep_sky_blue1"}
    )
