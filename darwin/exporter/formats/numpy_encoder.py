import json
from typing import Any

import numpy as np


class NumpyEncoder(json.JSONEncoder):
    """
    Holds auxiliary functions to bridge numpy functionality with Python primitive types which are
    JSON friendly.
    """

    def default(self, obj: Any) -> Any:
        """
        Converts the given numpy object into a Python's primitive type.

        Parameters
        ----------
        obj : Any
            The object to convert.

        Returns
        -------
        Any
            The converted object.
        """
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NumpyEncoder, self).default(obj)
