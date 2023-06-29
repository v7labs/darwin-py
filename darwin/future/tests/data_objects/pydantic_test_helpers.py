from typing import List, Type

import pytest

from darwin.future.data_objects.pydantic_base import DefaultDarwin


def test_required_fields(
    pydantic_object: Type[DefaultDarwin], required_fields: List[str] = [], not_required_fields: List[str] = []
) -> None:
    # TODO implement

    raise NotImplementedError


def test_field_types(
    pydantic_object: Type[DefaultDarwin], fields_to_test: List[str] = [], invalid_values: List[UnknownType] = []
) -> None:
    # TODO implement

    raise NotImplementedError

    # dataset = WFDataset.parse_file(validate_dataset_json)

    # fields = ["id", "name", "instructions"]

    # # Test missing fields
    # for key in fields:
    #     with pytest.raises(ValidationError) as excinfo:
    #         working_dataset = dataset.copy().dict()
    #         del working_dataset[key]
    #         WFDataset.parse_obj(working_dataset)

    #     assert "value_error.missing" in (err_string := str(excinfo.value))
    #     assert err_string.startswith(f"1 validation error for WFDataset\n{key}")

    # # Test invalid types
    # for key in fields:
    #     with pytest.raises(ValidationError) as excinfo:
    #         working_dataset = dataset.copy().dict()
    #         working_dataset[key] = InvalidValueForTest()  # type: ignore
    #         WFDataset.parse_obj(working_dataset)

    #     assert "type expected" in (err_string := str(excinfo.value))
    #     assert err_string.startswith(f"1 validation error for WFDataset\n{key}")
