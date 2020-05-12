# Requirements: pytorch, torchvision, pycocotools
from .dataset import (
    get_dataset,
    Dataset,
    ClassificationDataset,
    InstanceSegmentationDataset,
    SemanticSegmentationDataset,
)

try:
    import torch
    import torchvision
except ImportError:
    raise ImportError(f"pytorch and torchvision required. Install it using: pip install torch torchvision")

try:
    import pycocotools
except ImportError:
    raise ImportError(f"pycocotools required. Install it using: pip install cython; pip install -U 'git+https://github.com/cocodataset/cocoapi.git#subdirectory=PythonAPI'")
