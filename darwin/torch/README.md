# PyTorch


This is an example on how to fetch a dataset from Darwin, splitting it into 70% for training, 20% for validation, 10% test, and getting the train partition, using the function `get_dataset`:

```
from darwin.torch.dataset import get_dataset

db = get_dataset('bird-species', image_set="train", val_percentage=0.2, test_percentage=0.1)
```

The function `get_dataset` also accepts a list of transform as parameter uisng the parameter `transforms`. It also allows you to select the groundtrurth data you are interested in, such as `instance_segmentation`, `image_classification`, or `semantic_segmentation`. Finally, it also accepts a Darwin client as a parameter, containing your authenticating credentials in the Darwin.

```
from darwin.torch.dataset import get_dataset
from darwin.client import Client
import darwin.torch.transforms as T

trfs = T.Compose([T.RandomHorizontalFlip(), T.ToTensor()])
cli = Client(...)

db = get_dataset('bird-species', image_set="val", val_percentage=0.2, test_percentage=0.1, transforms=trfs, client=cli, mode="instance_segmentation")
```

Other advanced options include: fixing the seed for random splitting using `split_seed=INT`, force re-fetching a dataset discarding the local copy using `force_fetching=True`, and force a re-split of the dataset using `force_resplit=True`.

```
from darwin.torch.dataset import get_dataset
from darwin.client import Client
import darwin.torch.transforms as T

trfs = T.Compose([T.RandomHorizontalFlip(), T.ToTensor()])
cli = Client(...)

db = get_dataset('bird-species', image_set="val", val_percentage=0.25, transforms=trfs, client=cli, mode="image_classification"
        force_fetching=True, seed=42)
```
