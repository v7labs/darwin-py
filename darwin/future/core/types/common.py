from pydantic import ConstrainedStr

from darwin.future.data_objects import validators as darwin_validators


class TeamSlug(ConstrainedStr):
    """Team slug type"""

    min_length = 1
    max_length = 100

    validator = darwin_validators.parse_name
