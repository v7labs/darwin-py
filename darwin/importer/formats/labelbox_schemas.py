bounding_box = {
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
    "$id": "https://darwin.v7labs.com/schemas/polygon",
    "description": "Schema of a Polygon",
    "title": "Polygon",
    "default": [{"x": 1.2, "y": 2.5}, {"x": 2.5, "y": 3.6}, {"x": 1.2, "y": 2.5}],
    "examples": [[{"x": 1.2, "y": 2.5}, {"x": 2.5, "y": 3.6}, {"x": 1.2, "y": 2.5}], []],
    "type": "array",
    "items": point,
}


label_object = {
    "$id": "https://darwin.v7labs.com/schemas/label_object",
    "description": "An object belonging to the objects array from a Label",
    "title": "Label Object",
    "default": {"title": "Banana", "point": {"x": 3665.814, "y": 351.628}},
    "examples": [
        {"title": "Banana", "point": {"x": 3665.814, "y": 351.628}},
        {"title": "Orange", "bbox": {"top": 1.2, "left": 2.5, "height": 10, "width": 20}},
        {"title": "Apple", "polygon": [{"x": 1.2, "y": 2.5}, {"x": 2.5, "y": 3.6}, {"x": 1.2, "y": 2.5}]},
    ],
    "type": "object",
    "required": ["title"],
    "properties": {"title": {"type": "string"}},
    "oneOf": [
        {"required": ["point"], "properties": {"point": point}},
        {"required": ["bbox"], "properties": {"bbox": bounding_box}},
        {"required": ["polygon"], "properties": {"polygon": polygon}},
    ],
}

labelbox_file = {
    "$id": "https://darwin.v7labs.com/schemas/label_file",
    "description": "A Labelbox file, equivalent to a Darwin AnnotationFile",
    "title": "Labelbox File",
    "default": {
        "Label": {"objects": [{"title": "Banana", "point": {"x": 3665.814, "y": 351.628},}]},
        "External ID": "demo-image-7.jpg",
    },
    "examples": [
        {
            "Label": {"objects": [{"title": "Banana", "point": {"x": 3665.814, "y": 351.628},}]},
            "External ID": "demo-image-7.jpg",
        }
    ],
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
    "$id": "https://darwin.v7labs.com/schemas/export",
    "description": "A Labelbox export",
    "title": "Export",
    "default": [
        {
            "Label": {"objects": [{"title": "Banana", "point": {"x": 3665.814, "y": 351.628},}]},
            "External ID": "demo-image-7.jpg",
        }
    ],
    "examples": [
        [
            {
                "Label": {"objects": [{"title": "Banana", "point": {"x": 3665.814, "y": 351.628},}]},
                "External ID": "demo-image-7.jpg",
            },
            {
                "Label": {"objects": [{"title": "Orange", "point": {"x": 0.814, "y": 0.628},}]},
                "External ID": "demo-image-8.jpg",
            },
        ]
    ],
    "type": "array",
    "items": labelbox_file,
}

