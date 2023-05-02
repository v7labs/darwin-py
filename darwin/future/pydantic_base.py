from pydantic import BaseModel


class DefaultDarwin(BaseModel):
    """Default Darwin-Py pydantic settings for meta information.
    Default settings include:
        - auto validating variables on setting/assignment
        - underscore attributes are private
        - objects are passed by reference to prevent unnecesary data copying
    """

    class Config:
        validate_assignment = True
        underscore_attrs_are_private = True
        copy_on_model_validation = "none"
