from pydantic import BaseModel, ConfigDict


class DefaultDarwin(BaseModel):
    """
    Default Darwin-Py pydantic settings for meta information.
    Default settings include:
        - auto validating variables on setting/assignment
        - underscore attributes are private
        - objects are passed by reference to prevent unnecesary data copying
    """

    # TODO[pydantic]: The following keys were removed: `underscore_attrs_are_private`, `copy_on_model_validation`.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-config for more information.
    model_config = ConfigDict(validate_assignment=True)
