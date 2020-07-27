# Requirements: pytorch, torchvision, pycocotools
try:
    import torch  # noqa
    import torchvision  # noqa
except ImportError:
    raise ImportError(
        f"darwin.torch requires pytorch and torchvision. Install it using: pip install torch torchvision"
    ) from None

from .dataset import *  # noqa
