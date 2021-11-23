bounding_box = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://darwin.v7labs.com/schemas/bounding_box",
    "description": "Schema of a Bounding Box",
    "title": "Bounding Box",
    "default": {"top": 1.2, "left": 2.5, "height": 10, "width": 20},
    "examples": [{"top": 0, "left": 0, "height": 10, "width": 20}],
    "type": "object",
    "properties": {
        "top": {"type": "number"},
        "left": {"type": "number"},
        "height": {"type": "number", "minimum": 0},
        "width": {"type": "number", "minimum": 0},
    },
    "required": ["top", "left", "height", "width"],
}

point = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://darwin.v7labs.com/schemas/point",
    "description": "Schema of a Point",
    "title": "Point",
    "default": {"x": 1.2, "y": 2.5},
    "examples": [{"x": 1.2, "y": 2.5}, {"x": 0, "y": 1}],
    "type": "object",
    "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
    "required": ["x", "y"],
}

polygon = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://darwin.v7labs.com/schemas/polygon",
    "description": "Schema of a Polygon",
    "title": "Polygon",
    "default": [{"x": 1.2, "y": 2.5}, {"x": 2.5, "y": 3.6}, {"x": 1.2, "y": 2.5}],
    "examples": [[{"x": 1.2, "y": 2.5}, {"x": 2.5, "y": 3.6}, {"x": 1.2, "y": 2.5}], []],
    "type": "array",
    "items": point,
}


label_object = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["title"],
    "properties": {"title": {"type": "string"}},
    "oneOf": [
        {"required": ["point"], "properties": {"point": point}},
        {"required": ["bbox"], "properties": {"bbox": bounding_box}},
        {"required": ["polygon"], "properties": {"polygon": polygon}},
    ],
}

label = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "Label": {
            "type": "object",
            "properties": {"objects": {"type": "array", "items": label_object}},
            "required": ["objects"],
        },
        "External ID": {"type": "string"},
    },
    "required": ["Label", "External ID"],
}

labelbox_export = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://darwin.v7labs.com/schemas/export",
    "description": "A Labelbox export",
    "title": "Export",
    "default": {"x": 1.2, "y": 2.5},
    "examples": [{"x": 1.2, "y": 2.5}, {"x": 0, "y": 1}],
    "type": "array",
    "items": label,
}

