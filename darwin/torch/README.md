# PyTorch

This toolbox include some funcitonality to load your datasets ready to be plugged into Pytorch's DataLoaders. For that you can use the function `get_dataset`:

```
get_dataset("/PATH/TO/YOUR/DATASET", DATASET_TYPE [, PARTITION, RELEASE_NAME, TRANSFORMS])
```

Here is an example of how to load the `bird-species` dataset ready for instance segmentation using the "instance_segmentation" `dataset_type` (alternatively you can use "classification" or "semantic_segmentation" for different taks):

```
from darwin.torch import get_dataset

db = get_dataset("/datasets/bird-species", dataset_type="instance_segmentation")
```

You can use this function in combination with the `split_dataset` function to load only a given partition, and also provide a list of transformations:

```
from darwin.dataset import split_dataset
from darwin.torch import get_dataset
import darwin.torch.transforms as T

split_dataset("/datasets/bird-species", val_percentage=0.2, test_percentage=0)

trfs_train = T.Compose([T.RandomHorizontalFlip(), T.ToTensor()])
db_train = get_dataset("/datasets/bird-species", dataset_type="instance_segmentation", partition="train", transform=trfs_val)

trfs_val = T.Compose([T.ToTensor()])
db_val = get_dataset("/datasets/bird-species", dataset_type="instance_segmentation", partition="val", transform=trfs_train)
```
