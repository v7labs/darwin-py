from darwin.future.core.client import JSONType

CREATE_DATASET_RETURN_RAW: JSONType = {
    "active": True,
    "annotation_hotkeys": {},
    "annotators_can_create_tags": True,
    "annotators_can_instantiate_workflows": True,
    "anyone_can_double_assign": False,
    "archived": False,
    "archived_at": None,
    "default_workflow_template_id": 1337,
    "id": 13371337,
    "instructions": "",
    "name": "test_dataset",
    "num_classes": 0,
    "num_images": 0,
    "owner_id": 101,
    "parent_id": None,
    "pdf_fit_page": True,
    "progress": 0.0,
    "public": None,
    "reviewers_can_annotate": False,
    "slug": "test_dataset",
    "team_id": 123,
    "team_slug": "test-team",
    "thumbnails": [],
    "version": 1,
    "work_prioritization": "inserted_at:desc",
    "work_size": 30,
    "workflow_ids": [],
}

CREATE_ITEM_RETURN_RAW: JSONType = {
    # fmt: off
    "items": [
        {
            "id": "test_id", 
            "name": "test_dataset",
            "path": "test_path",
            "slots": [
                {
                    "file_name": "slot_file_name",
                    "slot_name": "slot_name",
                }
            ],
        }
    ]
    # fmt: on
}
