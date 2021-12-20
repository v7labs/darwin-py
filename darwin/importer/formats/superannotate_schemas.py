ellipse = {
    "$id": "https://darwin.v7labs.com/schemas/supperannotate/ellipse",
    "description": "Schema of an Ellipse",
    "title": "Ellipse",
    "default": {"type": "ellipse", "cx": 377.46, "cy": 806.18, "rx": 316.36, "ry": 134.18, "angle": 0, "classId": 1},
    "examples": [
        {"type": "ellipse", "cx": 377.46, "cy": 806.18, "rx": 316.36, "ry": 134.18, "angle": 14.66, "classId": 1}
    ],
    "type": "object",
    "properties": {
        "classId": {"type": "integer"},
        "cx": {"type": "number"},
        "cy": {"type": "number"},
        "rx": {"type": "number"},
        "ry": {"type": "number"},
        "angle": {"type": "number"},
        "ẗype": {"enum": ["ellipse"]},
    },
    "required": ["cx", "cy", "rx", "ry", "angle", "type", "classId"],
}

point = {
    "$id": "https://darwin.v7labs.com/schemas/supperannotate/point",
    "description": "Schema of a Point",
    "title": "Point",
    "default": {"type": "point", "x": 1.2, "y": 2.5, "classId": 1},
    "examples": [{"type": "point", "x": 1.2, "y": 2.5, "classId": 1}, {"type": "point", "x": 0, "y": 1, "classId": 2}],
    "type": "object",
    "properties": {
        "classId": {"type": "integer"},
        "x": {"type": "number"},
        "y": {"type": "number"},
        "ẗype": {"enum": ["point"]},
    },
    "required": ["x", "y", "type", "classId"],
}


superannotate_export = {
    "type": "object",
    "properties": {
        "instances": {"type": "array", "items": {"oneOf": [point, ellipse]},},
        "metadata": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}},
    },
    "required": ["instances", "metadata"],
}

classes_export = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["name", "id"],
        "properties": {"name": {"type": "string"}, "id": {"type": "integer"}},
    },
}
