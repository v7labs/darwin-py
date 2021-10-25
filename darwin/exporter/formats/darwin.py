import darwin.datatypes as dt


def build_image_annotation(annotation_file: dt.AnnotationFile):
    annotations = []
    for annotation in annotation_file.annotations:
        payload = {
            annotation.annotation_class.annotation_type: build_annotation_data(annotation),
            "name": annotation.annotation_class.name,
        }

        if (
            annotation.annotation_class.annotation_type == "complex_polygon"
            or annotation.annotation_class.annotation_type == "polygon"
        ) and "bounding_box" in annotation.data:
            payload["bounding_box"] = annotation.data["bounding_box"]

        annotations.append(payload)

    return {
        "annotations": annotations,
        "image": {
            "filename": annotation_file.filename,
            "height": annotation_file.image_height,
            "width": annotation_file.image_width,
            "url": annotation_file.image_url,
        },
    }


def build_annotation_data(annotation: dt.Annotation):
    if annotation.annotation_class.annotation_type == "complex_polygon":
        return {"path": annotation.data["paths"]}

    if annotation.annotation_class.annotation_type == "polygon":
        return dict(filter(lambda item: item[0] != "bounding_box", annotation.data.items()))

    return dict(annotation.data)
