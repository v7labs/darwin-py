class_map = {"type": "object", "patternProperties": {"^([0-9]+)+$": {"type": "string"}}, "additionalProperties": False}

nifti_image_label_pair = {
    "type": "object",
    "properties": {
        "image": {"type": "string"},
        "label": {"type": "string"},
        "class_map": class_map,
        "mode": {"type": "string", "enum": ["image", "video", "instances"]},
    },
    "required": ["image", "label", "class_map"],
    "additionalProperties": False,
}

nifti_import_schema = {
    "type": "object",
    "properties": {"data": {"type": "array", "items": nifti_image_label_pair}},
    "required": ["data"],
    "additionalProperties": False,
}
