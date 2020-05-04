from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Set, Optional, Union
from darwin.utils import secure_continue_request


@dataclass(frozen=True, eq=True)
class AnnotationClass:
    name: str
    annotation_type: str


@dataclass(frozen=True, eq=True)
class Annotation:
    annotation_class: AnnotationClass
    data: any


@dataclass
class AnnotationFile:
    path: Path
    filename: str
    annotation_classes: Set[AnnotationClass]
    annotations: List[Annotation]


@dataclass
class RemoteFile:
    remote_id: int
    filename: str

    # def get_classes(self):
    #     return Set([annotation.annotation_class for annotation in self.annotations])


def make_bounding_box(class_name, x, y, w, h):
    return Annotation(
        AnnotationClass(class_name, "bounding_box"),
        {"x": round(x, 3), "y": round(y, 3), "w": round(w, 3), "h": round(h, 3)},
    )


def make_polygon(class_name, point_path):
    return Annotation(AnnotationClass(class_name, "polygon"), {"path": point_path})


class AnnotationImport(ABC):
    @abstractmethod
    def parse_file(self, path: Path) -> Optional[AnnotationFile]:
        return None


def build_main_annotations_lookup_table(annotation_classes):
    lookup = {}
    for cls in annotation_classes:
        for annotation_type in cls["annotation_types"]:
            if annotation_type["granularity"] == "main":
                if annotation_type["name"] not in lookup:
                    lookup[annotation_type["name"]] = {}

                lookup[annotation_type["name"]][cls["name"]] = cls["id"]
    return lookup


def import_annotations(
    dataset: "RemoteDataset",
    importer: AnnotationImport,
    file_paths: List[Union[str, Path]],
):
    print("Fetching remote file list...")
    remote_files = {f["filename"]: f["id"] for f in dataset.fetch_remote_files()}
    print("Fetching remote class list...")
    remote_classes = build_main_annotations_lookup_table(dataset.fetch_remote_classes())

    print("Retrieving local annotations ...")
    local_files = []
    local_files_missing_remotely = []
    # TODO: this could be done in parallell
    for file_path in map(Path, file_paths):
        files = file_path.glob("**/*") if file_path.is_dir() else [file_path]
        for f in files:
            parsed_file = importer.parse_file(f)
            if not parsed_file:
                continue
            # clear to save memory
            parsed_file.annotations = []
            if parsed_file.filename not in remote_files:
                local_files_missing_remotely.append(parsed_file)
                continue
            local_files.append(parsed_file)
    print(
        f"{len(local_files) + len(local_files_missing_remotely)} annotation file(s) found."
    )
    if local_files_missing_remotely:
        print(
            f"{len(local_files_missing_remotely)} file(s) are missing from the dataset"
        )
        for local_file in local_files_missing_remotely:
            print(f"\t{local_file.path}: '{local_file.filename}'")

        if not secure_continue_request():
            return

    local_classes_missing_remotely = set()
    for local_file in local_files:
        for cls in local_file.annotation_classes:
            if cls.name not in remote_classes[cls.annotation_type]:
                local_classes_missing_remotely.add(cls)

    print(f"{len(local_classes_missing_remotely)} classes are missing remotely.")
    if local_classes_missing_remotely:
        print("About to create the following classes")
        for missing_class in local_classes_missing_remotely:
            print(f"\t{missing_class.name}, type: {missing_class.annotation_type}")
        if not secure_continue_request():
            return
        for missing_class in local_classes_missing_remotely:
            dataset.create_annotation_class(
                missing_class.name, missing_class.annotation_type
            )

            # Refetch classes to update mappings
            remote_classes = build_main_annotations_lookup_table(
                dataset.fetch_remote_classes()
            )

    # Need to re parse the files since we didn't save the annotations in memory
    for local_file in local_files:
        print(f"importing {local_file.path}")
        parsed_file = importer.parse_file(f)
        image_id = remote_files[parsed_file.filename]
        _import_annotations(
            dataset.client, image_id, remote_classes, parsed_file.annotations
        )


def _import_annotations(client: "Client", id: int, remote_classes, annotations):
    serialized_annotations = []
    for annotation in annotations:
        annotation_class = annotation.annotation_class
        annotation_class_id = remote_classes[annotation_class.annotation_type][
            annotation_class.name
        ]
        serialized_annotations.append(
            {
                "annotation_class_id": annotation_class_id,
                "data": {annotation_class.annotation_type: annotation.data},
            }
        )
    client.post(
        f"/dataset_images/{id}/import", payload={"annotations": serialized_annotations}
    )
