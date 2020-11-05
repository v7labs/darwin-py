from pathlib import Path
from typing import Callable, List, Union

from tqdm import tqdm

import darwin.datatypes as dt
from darwin.utils import secure_continue_request


def build_main_annotations_lookup_table(annotation_classes):
    lookup = {}
    for cls in annotation_classes:
        for annotation_type in cls["annotation_types"]:
            if annotation_type["granularity"] == "main":
                if annotation_type["name"] not in lookup:
                    lookup[annotation_type["name"]] = {}

                lookup[annotation_type["name"]][cls["name"]] = cls["id"]
    return lookup


def find_and_parse(
    remote_files: List[str],
    importer: Callable[[Path], Union[List[dt.AnnotationFile], dt.AnnotationFile, None]],
    file_paths: List[Union[str, Path]],
) -> (List[dt.AnnotationFile], List[dt.AnnotationFile]):
    local_files = []
    local_files_missing_remotely = []
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
                if parsed_file.filename not in remote_files:
                    local_files_missing_remotely.append(parsed_file)
                    continue
                local_files.append(parsed_file)
    return local_files, local_files_missing_remotely


def build_attribute_lookup(dataset):
    attributes = dataset.fetch_remote_attributes()
    lookup = {}
    for attribute in attributes:
        class_id = attribute["class_id"]
        if class_id not in lookup:
            lookup[class_id] = {}
        lookup[class_id][attribute["name"]] = attribute["id"]
    return lookup


def import_annotations(
    dataset: "RemoteDataset",
    importer: Callable[[Path], Union[List[dt.AnnotationFile], dt.AnnotationFile, None]],
    file_paths: List[Union[str, Path]],
):
    print("Fetching remote file list...")
    remote_files = {f.filename: f.id for f in dataset.fetch_remote_files()}
    print("Fetching remote class list...")
    remote_classes = build_main_annotations_lookup_table(dataset.fetch_remote_classes())
    attributes = build_attribute_lookup(dataset)

    print("Retrieving local annotations ...")
    local_files = []
    local_files_missing_remotely = []
    local_files, local_files_missing_remotely = find_and_parse(remote_files, importer, file_paths)

    print(f"{len(local_files) + len(local_files_missing_remotely)} annotation file(s) found.")
    if local_files_missing_remotely:
        print(f"{len(local_files_missing_remotely)} file(s) are missing from the dataset")
        for local_file in local_files_missing_remotely:
            print(f"\t{local_file.path}: '{local_file.filename}'")

        if not secure_continue_request():
            return

    local_classes_missing_remotely = set()
    for local_file in local_files:
        for cls in local_file.annotation_classes:
            annotation_type = cls.annotation_internal_type or cls.annotation_type
            # Only add the new class if it doesn't exist remotely already
            if annotation_type in remote_classes and cls.name in remote_classes[annotation_type]:
                continue
            # Only add the new class if it's not included in the list of the missing classes already
            if cls.name in [missing_class.name for missing_class in local_classes_missing_remotely]:
                continue
            local_classes_missing_remotely.add(cls)

    print(f"{len(local_classes_missing_remotely)} classes are missing remotely.")
    if local_classes_missing_remotely:
        print("About to create the following classes")
        for missing_class in local_classes_missing_remotely:
            print(
                f"\t{missing_class.name}, type: {missing_class.annotation_internal_type or missing_class.annotation_type}"
            )
        if not secure_continue_request():
            return
        for missing_class in local_classes_missing_remotely:
            dataset.create_annotation_class(
                missing_class.name, missing_class.annotation_internal_type or missing_class.annotation_type
            )

            # Refetch classes to update mappings
            remote_classes = build_main_annotations_lookup_table(dataset.fetch_remote_classes())

    # Need to re parse the files since we didn't save the annotations in memory
    for local_path in set(local_file.path for local_file in local_files):
        print(f"importing {local_path}")
        parsed_files = importer(local_path)
        if type(parsed_files) is not list:
            parsed_files = [parsed_files]
        # remove files missing on the server
        parsed_files = [parsed_file for parsed_file in parsed_files if parsed_file not in local_files_missing_remotely]
        for parsed_file in tqdm(parsed_files):
            print(parsed_file.filename, remote_files)
            image_id = remote_files[parsed_file.filename]
            _import_annotations(dataset.client, image_id, remote_classes, attributes, parsed_file.annotations, dataset)


def _handle_subs(annotation, data, attributes):
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


def _import_annotations(client: "Client", id: int, remote_classes, attributes, annotations, dataset):
    serialized_annotations = []
    for annotation in annotations:
        annotation_class = annotation.annotation_class
        annotation_type = annotation_class.annotation_internal_type or annotation_class.annotation_type
        annotation_class_id = remote_classes[annotation_type][annotation_class.name]

        if isinstance(annotation, dt.VideoAnnotation):
            data = annotation.get_data(
                only_keyframes=True,
                post_processing=lambda annotation, data: _handle_subs(
                    annotation, _handle_complex_polygon(annotation, data), attributes
                ),
            )
        else:
            data = {annotation_class.annotation_type: annotation.data}
            data = _handle_complex_polygon(annotation, data)
            data = _handle_subs(annotation, data, attributes)

        serialized_annotations.append({"annotation_class_id": annotation_class_id, "data": data})

    if client.feature_enabled("WORKFLOW", dataset.team):
        res = client.post(f"/dataset_items/{id}/import", payload={"annotations": serialized_annotations})
        if res.get("status_code") != 200:
            print(f"warning, failed to upload annotation to {id}", res)
    else:
        client.post(f"/dataset_images/{id}/import", payload={"annotations": serialized_annotations})
