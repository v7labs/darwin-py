# Dataset toolbox for Pytorch

This module includes some funcitonality to import your datasets ready to be plugged into Pytorch's DataLoaders. This can be done using `get_dataset()`:

```python
get_dataset("/PATH/TO/YOUR/DATASET", DATASET_TYPE [, PARTITION, SPLIT_TYPE, RELEASE_NAME, TRANSFORMS])
```

Here is an example of how to load the `bird-species` dataset ready to be used in a instance segmentation task using `"instance_segmentation"` as `dataset_type` (alternatively you can use `"classification"` or `"semantic_segmentation"` for those other tasks):

```python
from darwin.torch import get_dataset

db = get_dataset("/datasets/bird-species", dataset_type="instance_segmentation")
```

You can use this function in combination with `split_dataset()` to create and load different partitions:

```python
from darwin.dataset.utils import split_dataset
from darwin.torch import get_dataset
import darwin.torch.transforms as T

split_dataset("/datasets/bird-species", val_percentage=20, test_percentage=0)

trfs_train = T.Compose([T.RandomHorizontalFlip(), T.ToTensor()])
db_train = get_dataset("/datasets/bird-species", dataset_type="instance_segmentation", \
    partition="train", split_type="stratified", transform=trfs_train)

trfs_val = T.ToTensor()
db_val = get_dataset("/datasets/bird-species", dataset_type="instance_segmentation", \
    partition="val", split_type="stratified", transform=trfs_val)

print(db_train)
# Returns:
# InstanceSegmentationDataset():
#   Root: /datasets/bird-species
#   Number of images: 1528
#   Number of classes: 3
```
