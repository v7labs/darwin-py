# Requirements: pytorch, torchvision, pycocotools
try:
    import torch  # noqa
    import torchvision  # noqa
except ImportError:
    raise ImportError(
        f"darwin.torch requires pytorch and torchvision. Install it using: pip install torch torchvision"
    ) from None

try:
    import pycocotools  # noqa
except ImportError:
    raise ImportError(
        f"darwin.torch requires pycocotools. Install it using: pip install cython; pip install -U 'git+https://github.com/cocodataset/cocoapi.git#subdirectory=PythonAPI'"
    ) from None

from .dataset import (
    ClassificationDataset,
    DarwinDataset,
    InstanceSegmentationDataset,
    SemanticSegmentationDataset,
    get_dataset,
)
