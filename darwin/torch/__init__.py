import sys
from pathlib import Path

try:
    import torchvision  # noqa

    # Here we remove `darwin` directory from `sys.path` to force the importer
    # to import the library `torch`, rather than the internal package.
    # This hack resolves this naming conflict for Sphinx.
    for path in sys.path:
        path_str = str(Path("darwin-py") / "darwin")
        if path.endswith(path_str):
            sys.path.remove(path)

    import torch  # noqa
except ImportError:
    raise ImportError(
        f"darwin.torch requires pytorch and torchvision. Install it using: pip install torch torchvision"
    ) from None

from .dataset import get_dataset  # noqa
