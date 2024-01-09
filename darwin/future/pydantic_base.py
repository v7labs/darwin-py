from pydantic import BaseModel, ConfigDict


class DefaultDarwin(BaseModel):
    """Default Darwin-Py pydantic settings for meta information.
    Default settings include:
        - auto validating variables on setting/assignment
        - underscore attributes are private
        - objects are passed by reference to prevent unnecesary data copying
    """

    model_config = ConfigDict(validate_assignment=True, protected_namespaces=())
