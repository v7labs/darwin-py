# PyTorch


The library currently supports the following datasets depending on the type of model they are going to be used along with: `ClassificationDataset`, `InstanceSegmentationDataset`, `SemanticSegmentationDataset`.

There exists as well an empty class `BaseDataset` type that can be customized by the user accortdingly and whose only function is to fetch the dataset passed as argument (see example below).

The following script would fetch the `bird-species` dataset from Darwin, split it into: 70% for training, 20% for validation, and 10% test; and get the train partition:

```
from darwin.client import Client
from darwin.torch.dataset import ClassificationDataset, InstanceSegmentationDataset, SemanticSegmentationDataset, BaseDataset
import darwin.torch.transforms as T

client = Client.login(email="******", password="******")

trfs = [T.RandomHorizontalFlip(), T.ToTensor()]

my_classification_dataset = ClassificationDataset('bird-species', image_set="val", val_percentage=0.25, transforms=trfs, client=client)
# or
my_instanceSeg_dataset = InstanceSegmentationDataset('bird-species', image_set="val", val_percentage=0.25, transforms=trfs, client=client)
#or
my_semanticSeg_dataset = SemanticSegmentationDataset('bird-species', image_set="val", val_percentage=0.25, transforms=trfs, client=client)
#or
my_basic_dataset = BaseDataset('bird-species', image_set="val", val_percentage=0.25, transforms=trfs, client=client)
```

All dataset classes accept: [1] Darwin dataset name, [2] and [3] partition set to be loaded and validation split percentage, [4] a list of transforms, and [5] a Darwin client, containing your authenticating credentials in Darwin.

Additional options include: fixing the seed for random splitting using `split_seed=INT`, force downloading/updating the dataset discarding the local copy using `force_fetching=True`, and force a re-split of the dataset using `force_resplit=True`.

```
my_classification_dataset = ClassificationDataset('bird-species', image_set="val", val_percentage=0.25, transforms=trfs, client=client, force_fetching=True, split_seed=42)

#print a data sample:
print(my_classification_dataset.__getitem__(0)
```