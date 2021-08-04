from pathlib import Path
from typing import TYPE_CHECKING, Callable, List, Tuple, Union

if TYPE_CHECKING:
    from darwin.client import Client
    from darwin.dataset import RemoteDataset

import darwin.datatypes as dt
from darwin.utils import secure_continue_request
from rich.progress import track


def build_main_annotations_lookup_table(annotation_classes):
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
    lookup = {}
    for cls in annotation_classes:
        for annotation_type in cls["annotation_types"]:
            if annotation_type in MAIN_ANNOTATION_TYPES:
                if annotation_type not in lookup:
                    lookup[annotation_type] = {}
                lookup[annotation_type][cls["name"]] = cls["id"]
    return lookup


def find_and_parse(
    importer: Callable[[Path], Union[List[dt.AnnotationFile], dt.AnnotationFile, None]],
    file_paths: List[Union[str, Path]],
) -> Tuple[List[dt.AnnotationFile], List[dt.AnnotationFile]]:
    # TODO: this could be done in parallel
    for file_path in map(Path, file_paths):
        files = file_path.glob("**/*") if file_path.is_dir() else [file_path]
        for f in files:
            # importer returns either None, 1 annotation file or a list of annotation files
            parsed_files = importer(f)
            if parsed_files is None:
                continue
            if type(parsed_files) is not list:
                parsed_files = [parsed_files]
            for parsed_file in parsed_files:
                # clear to save memory
                parsed_file.annotations = []
                yield parsed_file


def build_attribute_lookup(dataset):
    attributes = dataset.fetch_remote_attributes()
    lookup = {}
    for attribute in attributes:
        class_id = attribute["class_id"]
        if class_id not in lookup:
            lookup[class_id] = {}
        lookup[class_id][attribute["name"]] = attribute["id"]
    return lookup


def get_remote_files(dataset, filenames):
    """Fetches remote files from the datasets, in chunks of 100 filesnames at a time"""
    remote_files = {}
    for i in range(0, len(filenames), 100):
        chunk = filenames[i : i + 100]
        for remote_file in dataset.fetch_remote_files(
            {"types": "image,playback_video,video_frame", "filenames": ",".join(chunk)}
        ):
            remote_files[remote_file.full_path] = remote_file.id
    return remote_files


def _resolve_annotation_classes(annotation_classes: List[dt.AnnotationClass], classes_in_dataset, classes_in_team):
    local_classes_not_in_dataset = set()
    local_classes_not_in_team = set()

    for cls in annotation_classes:
        annotation_type = cls.annotation_internal_type or cls.annotation_type
        # Only add the new class if it doesn't exist remotely already
        if annotation_type in classes_in_dataset and cls.name in classes_in_dataset[annotation_type]:
            continue

        # Only add the new class if it's not included in the list of the missing classes already
        if cls.name in [missing_class.name for missing_class in local_classes_not_in_dataset]:
            continue
        if cls.name in [missing_class.name for missing_class in local_classes_not_in_team]:
            continue

        if annotation_type in classes_in_team and cls.name in classes_in_team[annotation_type]:
            local_classes_not_in_dataset.add(cls)
        else:
            local_classes_not_in_team.add(cls)
    return local_classes_not_in_dataset, local_classes_not_in_team


def import_annotations(
    dataset: "RemoteDataset",
    importer: Callable[[Path], Union[List[dt.AnnotationFile], dt.AnnotationFile, None]],
    file_paths: List[Union[str, Path]],
    append: bool,
):
    print("Fetching remote class list...")
    team_classes = dataset.fetch_remote_classes(True)
    classes_in_dataset = build_main_annotations_lookup_table([cls for cls in team_classes if cls["available"]])
    classes_in_team = build_main_annotations_lookup_table([cls for cls in team_classes if not cls["available"]])
    attributes = build_attribute_lookup(dataset)

    print("Retrieving local annotations ...")
    local_files = []
    local_files_missing_remotely = []
    parsed_files = list(find_and_parse(importer, file_paths))
    filenames = [parsed_file.filename for parsed_file in parsed_files]

    print("Fetching remote file list...")
    # This call will only filter by filename; so can return a superset of matched files across different paths
    # There is logic in this function to then include paths to narrow down to the single correct matching file
    remote_files = get_remote_files(dataset, filenames)
    for parsed_file in parsed_files:
        if parsed_file.full_path not in remote_files:
            local_files_missing_remotely.append(parsed_file)
        else:
            local_files.append(parsed_file)

    print(f"{len(local_files) + len(local_files_missing_remotely)} annotation file(s) found.")
    if local_files_missing_remotely:
        print(f"{len(local_files_missing_remotely)} file(s) are missing from the dataset")
        for local_file in local_files_missing_remotely:
            print(f"\t{local_file.path}: '{local_file.full_path}'")

        if not secure_continue_request():
            return

    local_classes_not_in_dataset, local_classes_not_in_team = _resolve_annotation_classes(
        [annotation_class for file in local_files for annotation_class in file.annotation_classes],
        classes_in_dataset,
        classes_in_team,
    )

    print(f"{len(local_classes_not_in_team)} classes needs to be created.")
    print(f"{len(local_classes_not_in_dataset)} classes needs to be added to {dataset.identifier}")

    if local_classes_not_in_team:
        print("About to create the following classes")
        for missing_class in local_classes_not_in_team:
            print(
                f"\t{missing_class.name}, type: {missing_class.annotation_internal_type or missing_class.annotation_type}"
            )
        if not secure_continue_request():
            return
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
        remote_classes = build_main_annotations_lookup_table(dataset.fetch_remote_classes())
    else:
        remote_classes = build_main_annotations_lookup_table(team_classes)

    # Need to re parse the files since we didn't save the annotations in memory
    for local_path in set(local_file.path for local_file in local_files):
        parsed_files = importer(local_path)
        if type(parsed_files) is not list:
            parsed_files = [parsed_files]
        # remove files missing on the server
        missing_files = [missing_file.full_path for missing_file in local_files_missing_remotely]
        parsed_files = [parsed_file for parsed_file in parsed_files if parsed_file.full_path not in missing_files]
        for parsed_file in track(parsed_files):
            image_id = remote_files[parsed_file.full_path]
            _import_annotations(
                dataset.client, image_id, remote_classes, attributes, parsed_file.annotations, dataset, append
            )


def _handle_subs(annotation, data, annotation_class_id, attributes):
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


def _handle_complex_polygon(annotation, data):
    if "complex_polygon" in data:
        del data["complex_polygon"]
        data["polygon"] = {"path": annotation.data["paths"][0], "additional_paths": annotation.data["paths"][1:]}
    return data


def _import_annotations(client: "Client", id: int, remote_classes, attributes, annotations, dataset, append):
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

    payload = {"annotations": serialized_annotations}
    if append:
        payload["overwrite"] = "false"
    res = client.post(f"/dataset_items/{id}/import", payload=payload)
    if res.get("status_code") != 200:
        print(f"warning, failed to upload annotation to {id}", res)
