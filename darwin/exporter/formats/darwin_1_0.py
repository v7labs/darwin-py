from pathlib import Path
from typing import Any, Dict, Iterable, List, Union

import orjson as json

import darwin.datatypes as dt
from darwin.exporter.formats.numpy_encoder import NumpyEncoder


def export(annotation_files: Iterable[dt.AnnotationFile], output_dir: Path) -> None:
    for id, annotation_file in enumerate(annotation_files):
        _export_file(annotation_file, id, output_dir)


def _export_file(annotation_file: dt.AnnotationFile, id: int, output_dir: Path):
    output: Dict[str, Any] = _build_json(annotation_file)
    output_file_path: Path = (output_dir / annotation_file.filename).with_suffix(".json")
    with open(output_file_path, "w") as f:
        op = json.dumps(output, option=json.OPT_INDENT_2 | json.OPT_SERIALIZE_NUMPY).decode("utf-8")
        f.write(op)


def _build_json(annotation_file: dt.AnnotationFile):
    if annotation_file.is_video:
        return _build_video_json(annotation_file)
    else:
        return _build_image_json(annotation_file)


def _build_image_json(annotation_file: dt.AnnotationFile):
    return {
        "image": {
            "seq": annotation_file.seq,
            "width": annotation_file.image_width,
            "height": annotation_file.image_height,
            "filename": annotation_file.filename,
            "original_filename": annotation_file.filename,
            "url": annotation_file.image_url,
            "thumbnail_url": annotation_file.image_thumbnail_url,
            "path": annotation_file.remote_path,
            "workview_url": annotation_file.workview_url,
            **_build_metadata(annotation_file),
        },
        "annotations": list(map(_build_annotation, annotation_file.annotations)),
    }


def _build_video_json(annotation_file: dt.AnnotationFile):
    return {
        "image": {
            "seq": annotation_file.seq,
            "frame_urls": annotation_file.frame_urls,
            "frame_count": len(annotation_file.frame_urls or []),
            "width": annotation_file.image_width,
            "height": annotation_file.image_height,
            "filename": annotation_file.filename,
            "original_filename": annotation_file.filename,
            "thumbnail_url": annotation_file.image_thumbnail_url,
            "url": annotation_file.image_url,
            "path": annotation_file.remote_path,
            "workview_url": annotation_file.workview_url,
            **_build_metadata(annotation_file),
        },
        "annotations": list(map(_build_annotation, annotation_file.annotations)),
    }


def _build_annotation(annotation):
    if isinstance(annotation, dt.VideoAnnotation):
        return _build_video_annotation(annotation)
    else:
        return _build_image_annotation(annotation)


def _build_author(author: dt.AnnotationAuthor) -> Dict[str, Any]:
    return {"full_name": author.name, "email": author.email}


def _build_sub_annotation(sub: dt.SubAnnotation) -> Dict[str, Any]:
    if sub.annotation_type == "instance_id":
        return {sub.annotation_type: {"value": sub.data}}
    elif sub.annotation_type == "attributes":
        return {sub.annotation_type: sub.data}
    elif sub.annotation_type == "text":
        return {sub.annotation_type: {"text": sub.data}}
    else:
        return {sub.annotation_type: sub.data}


def _build_authorship(annotation: Union[dt.VideoAnnotation, dt.Annotation]) -> Dict[str, Any]:
    annotators = {}
    if annotation.annotators:
        annotators = {"annotators": [_build_author(annotator) for annotator in annotation.annotators]}

    reviewers = {}
    if annotation.reviewers:
        reviewers = {"annotators": [_build_author(reviewer) for reviewer in annotation.reviewers]}

    return {**annotators, **reviewers}


def _build_video_annotation(annotation: dt.VideoAnnotation) -> Dict[str, Any]:
    return {
        **annotation.get_data(
            only_keyframes=False,
            post_processing=lambda annotation, _: _build_image_annotation(annotation, skip_slots=True),
        ),
        "name": annotation.annotation_class.name,
        "slot_names": annotation.slot_names,
        **_build_authorship(annotation),
    }


def _build_image_annotation(annotation: dt.Annotation, skip_slots: bool = False) -> Dict[str, Any]:
    json_subs = {}
    for sub in annotation.subs:
        json_subs.update(_build_sub_annotation(sub))

    base_json = {
        **json_subs,
        **_build_authorship(annotation),
        **_build_legacy_annotation_data(annotation.annotation_class, annotation.data),
        "name": annotation.annotation_class.name,
    }

    if skip_slots:
        return base_json
    else:
        return {**base_json, "slot_names": annotation.slot_names}


def _build_legacy_annotation_data(annotation_class: dt.AnnotationClass, data: Dict[str, Any]) -> Dict[str, Any]:
    if annotation_class.annotation_type == "complex_polygon":
        data["path"] = data["paths"][0]
        data["additional_paths"] = data["paths"][1:]
        del data["paths"]
        return {"complex_polygon": data}
    else:
        return {annotation_class.annotation_type: data}


def _build_metadata(annotation_file: dt.AnnotationFile):
    if len(annotation_file.slots) > 0 and annotation_file.slots[0].metadata:
        return {"metadata": annotation_file.slots[0].metadata}
    else:
        return {}
