import darwin.importer as importer
from darwin.client import Client
from darwin.importer import formats
from pathlib import Path

format_name = "darwin"
file_paths = ["/root/.darwin/summer-slam/annos"]
dataset_slug = "v7/brent-summer-slam"

config_dir = Path.home() / ".darwin" / "config.yaml"
client = Client.from_config(config_dir)

parser = dict(formats.supported_formats)[format_name]
dataset = client.get_remote_dataset(dataset_identifier=dataset_slug)

parsed_files = list(importer.find_and_parse(parser, file_paths))
filenames = [parsed_file.filename for parsed_file in parsed_files]

team_classes = dataset.fetch_remote_classes(True)
remote_classes = importer.build_main_annotations_lookup_table(team_classes)
attributes = importer.build_attribute_lookup(dataset)

remote_files = importer.get_remote_files(dataset, filenames)

def _import_annotations(client: "Client", id: int, remote_classes, attributes, annotations, dataset, append):
    serialized_annotations = []

    if(len(attributes) > 0 ):
        print("looking for")
    
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
    #if append:
    payload["overwrite"] = "false"
    res = client.post(f"/dataset_items/{id}/import", payload=payload)
    if res.get("status_code") != 200:
        print(f"warning, failed to upload annotation to {id}", res)


for parsed_file in parsed_files:
    image_id = remote_files[parsed_file.full_path]
    reparsed_file = parser(Path(parsed_file.full_path))
    _import_annotations(
        dataset.client, image_id, remote_classes, attributes, reparsed_file.annotations, dataset, False
    )





#########

dataset = client.get_remote_dataset(dataset_identifier=dataset_identifier)

parser = dict(formats.supported_formats)[format_name]

importer.import_annotations(dataset, parser, annotation_paths, append=true)