import sys
from pathlib import Path

try:
    import torchvision  # noqa

    # Here we remove `darwin_directory` from `sys.path` to force the importer
    # to import the library `torch`, rather than the internal package.
    # This hack resolves this naming conflict for Sphinx.
    darwin_directory = str(Path.home() / "darwin-py" / "darwin")
    if darwin_directory in sys.path:
        sys.path.remove(darwin_directory)

    import torch  # noqa
except ImportError:
    raise ImportError(
        f"darwin.torch requires pytorch and torchvision. Install it using: pip install torch torchvision"
    ) from None

from .dataset import get_dataset  # noqa
