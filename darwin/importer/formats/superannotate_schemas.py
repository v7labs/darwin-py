polygon = {
    "$id": "https://darwin.v7labs.com/schemas/supperannotate/polygon",
    "description": "Schema of a Polygon",
    "title": "Polygon",
    "default": {"type": "polygon", "points": [1, 2, 3, 4], "classId": 1},
    "examples": [
        {"type": "polygon", "points": [1, 2, 3, 4], "classId": 1},
        {"type": "polygon", "points": [], "classId": 1},
    ],
    "type": "object",
    "properties": {
        "classId": {"type": "integer"},
        "points": {"type": "array", "items": {"type": "number"}},
        "type": {"enum": ["polygon"]},
    },
    "required": ["points", "type", "classId"],
}

cuboid = {
    "$id": "https://darwin.v7labs.com/schemas/supperannotate/cuboid",
    "description": "Schema of a Cuboid",
    "title": "Cuboid",
    "default": {
        "type": "cuboid",
        "points": {
            "f1": {"x": 1223.1, "y": 587.5},
            "f2": {"x": 1540.3, "y": 1420.2},
            "r1": {"x": 1286.2, "y": 607.3},
            "r2": {"x": 1603.4, "y": 1440},
        },
        "classId": 1,
    },
    "examples": [
        {
            "type": "cuboid",
            "points": {
                "f1": {"x": 1223.1, "y": 587.5},
                "f2": {"x": 1540.3, "y": 1420.2},
                "r1": {"x": 1286.2, "y": 607.3},
                "r2": {"x": 1603.4, "y": 1440},
            },
            "classId": 1,
        }
    ],
    "type": "object",
    "properties": {
        "classId": {"type": "integer"},
        "type": {"enum": ["cuboid"]},
        "points": {
            "type": "object",
            "properties": {
                "f1": {
                    "type": "object",
                    "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
                    "required": ["x", "y"],
                },
                "f2": {
                    "type": "object",
                    "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
                    "required": ["x", "y"],
                },
                "r1": {
                    "type": "object",
                    "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
                    "required": ["x", "y"],
                },
                "r2": {
                    "type": "object",
                    "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
                    "required": ["x", "y"],
                },
            },
            "required": ["f1", "f2", "r1", "r2"],
        },
    },
    "required": ["points", "type", "classId"],
}

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
        "type": {"enum": ["ellipse"]},
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
        "type": {"enum": ["point"]},
    },
    "required": ["x", "y", "type", "classId"],
}


superannotate_export = {
    "type": "object",
    "properties": {
        "instances": {"type": "array", "items": {"oneOf": [point, ellipse, cuboid, polygon]},},
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
