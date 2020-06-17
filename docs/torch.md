# PyTorch bindings

This module includes some functionality to import your datasets ready to be plugged into your Pytorch-based libraries. For this, you can use `get_dataset()` function:

```
def get_dataset(dataset_slug, dataset_type [, partition, split, split_type, transform])
Input
----------
dataset_slug: str
  Slug of the dataset to retrieve
dataset_type: str
  The type of dataset [classification, instance-segmentation, semantic-segmentation]
partition: str
  Selects one of the partitions [train, val, test, None]. (Default: None)
split: str
  Selects the split that defines the percentages used. (Default: 'default')
split_type: str
  Heuristic used to do the split [random, stratified]. (Default: 'random')
transform : list[torchvision.transforms]
  List of PyTorch transforms. (Default: None)

Output
----------
dataset: LocalDataset
  API class to the local dataset
```

For now, it only support three types of dataset: `classification`, `instance-segmentation`, and `semantic-segmentation`. These different modes use different API classes, which load and pre-process the data in different ways, tailored for these specific tasks. If you need a different API or a different pre-processing for a different task you can take a look into the implementation of these APIs in `darwin.torch.dataset` and extend `LocalDataset` in the way it suits your needs best.

Finally, this is an example of how to load the `v7-demo/bird-species` dataset ready to be used in a instance segmentation task using `"instance-segmentation"` as `dataset_type`. First, we will pull it from Darwin using `darwin-py`'s CLI and will create train, validation, and test partitions:

```bash
darwin dataset pull v7-demo/bird-species
darwin dataset split v7-demo/bird-species --val-percentage 10 --test-percentage 20
```

Once downloaded, we can use `get_dataset()` to load the different partitions, and pass different transformations for train and validation splits (some basic transformations are implemented in `darwin.torch.transforms` but you can also use your own transformations):

```python
from darwin.torch import get_dataset
import darwin.torch.transforms as T

dataset_slug = "v7-demo/bird-species"

trfs_train = T.Compose([T.RandomHorizontalFlip(), T.ToTensor()])
db_train = get_dataset(dataset_slug, dataset_type="instance-segmentation", \
    partition="train", split_type="stratified", transform=trfs_train)

trfs_val = T.ToTensor()
db_val = get_dataset(dataset_slug, dataset_type="instance-segmentation", \
    partition="val", split_type="stratified", transform=trfs_val)

print(db_train)
# Returns:
# InstanceSegmentationDataset():
#   Root: /datasets/v7-demo/bird-species
#   Number of images: 1336
#   Number of classes: 3
```


## Darwin X Torchvision

This tutorial shows how to use the function `get_dataset()` in `darwin-py` to train an instance segmentaion model using Pytorch's [Torchvsion](https://github.com/pytorch/vision) on a dataset in Darwin. First, using `darwin-py`'s CLI, we will pull the dataset from Darwin and create train, validation, and test partitions.

```bash
darwin dataset pull v7-demo/bird-species
darwin dataset split v7-demo/bird-species --val-percentage 10 --test-percentage 20
```

Now, in Python, we will start by importing some `torchvision` and `darwin` functions, and by defining the function `get_instance_segmentation_model()` that we will use to instantiate a [Mask-RCNN](https://arxiv.org/abs/1703.06870) model using Torchvision's API.

```python
import torch
import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor

from darwin.torch import get_dataset
import darwin.torch.transforms as T


def collate_fn(batch):
    return tuple(zip(*batch))

def get_instance_segmentation_model(num_classes):
    # load an instance segmentation model pre-trained on COCO
    model = torchvision.models.detection.maskrcnn_resnet50_fpn(pretrained=True)

    # add a new bounding box predictor
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

    # add a new mask predictor
    in_features_mask = model.roi_heads.mask_predictor.conv5_mask.in_channels
    hidden_layer = 256
    model.roi_heads.mask_predictor = MaskRCNNPredictor(in_features_mask,
                                                       hidden_layer,
                                                       num_classes)
    return model
```

Then, we will load the dataset using `darwin-py`'s `get_dataset()` function, specifying the path to the dataset, the dataset type (in this case we need an `instance-segmentation` dataset), and the `train` partition. The dataset that we get back can be used directly into Pytorch's standard DataLoader.

```python
trfs_train = T.Compose([T.RandomHorizontalFlip(), T.ToTensor()])
dataset = get_dataset("v7-demo/bird-species", dataset_type="instance-segmentation",
                      partition="train", split_type="stratified", transform=trfs_train)
data_loader = torch.utils.data.DataLoader(dataset, batch_size=2, shuffle=True, num_workers=4, collate_fn=collate_fn)
```

Next, we instantiate the instance segmentation model and define the optimizer and the learning rate scheduler.

```python
device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')

# get the model using our helper function
num_classes = dataset.num_classes + 1 # number of classes in the dataset + background
model = get_instance_segmentation_model(num_classes)
model.to(device)

# construct an optimizer
params = [p for p in model.parameters() if p.requires_grad]
optimizer = torch.optim.SGD(params, lr=0.005, momentum=0.9, weight_decay=0.0005)
# and a learning rate scheduler
lr_scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.1)
```

And finally, we define our training loop and train the model for 10 full epochs.

```python
# let's train it for 10 epochs
for epoch in range(10):
    # train for one epoch, printing every 10 iterations
    acumm_loss = 0
    for i, (images, targets) in enumerate(data_loader):
        images = list(image.to(device) for image in images)
        targets = [{k: v.to(device) for k, v in t.items() if isinstance(v, torch.Tensor)} for t in targets]

        loss_dict = model(images, targets)
        losses = sum(loss for loss in loss_dict.values())

        optimizer.zero_grad()
        losses.backward()
        optimizer.step()
        acumm_loss += losses.cpu().item()
        if i % 10 == 0:
            print(f"Loss: {acumm_loss/10}")
            acumm_loss = 0

    lr_scheduler.step()
```


## Darwin X Detectron2

This tutorial shows how to train [Detectron2](https://github.com/facebookresearch/detectron2) models in your Darwin datasets. If you do not have Detectron2 installed yet, follow these [installation instructions](https://github.com/facebookresearch/detectron2/blob/master/INSTALL.md).

Detectron2 organizes the datasets in `DatasetCatalog`, so the only thing we will need to do is to register our Darwin dataset in this catalog. For this, `darwin-py` provides thes `detectron2_register_dataset`, which takes the following parameters:

```
detectron2_register_dataset(dataset_slug [, partition, split, split_type, release_name, evaluator_type])
Input
----------
dataset_slug: Path, str
  Slug of the dataset you want to register
partition: str
  Selects one of the partitions [train, val, test]. If None, loads the whole dataset. (default: None)
split
  Selects the split that defines the percetages used (use 'default' to select the default split)
split_type: str
  Heuristic used to do the split [random, stratified] (default: stratified)
release_name: str
  Version of the dataset. If None, takes the latest (default: None)
evaluator_type: str
  Evaluator to be used in the val and test sets (default: None)

Output
----------
catalog_name: str
  Name used to register this dataset partition in DatasetCatalog
```

Here's an example of how to use this function to register a Darwin dataset, and train an instance segmentation model on it. First, and as we did before, we will start by pulling the dataset from Darwin and splitting it into train and validation from the command line:

```bash
darwin dataset pull v7-demo/bird-species
darwin dataset split v7-demo/bird-species --val-percentage 10
```

Now in Python, we will import some `detectron2` utils and we will register the Darwin dataset into Detectron2's catalog.

```python
import os
# import some common Detectron2 and Darwin utilities
from detectron2.utils.logger import setup_logger
from detectron2 import model_zoo
from detectron2.engine import DefaultTrainer
from detectron2.config import get_cfg
from detectron2.data import MetadataCatalog, build_detection_test_loader
from detectron2.evaluation import COCOEvaluator, inference_on_dataset
from darwin.torch.utils import detectron2_register_dataset


# Register both training and validation sets
dataset_slug = 'v7-demo/bird-species'
dataset_train = detectron2_register_dataset(dataset_slug, partition='train', split_type='stratified')
dataset_val = detectron2_register_dataset(dataset_slug, partition='val', split_type='stratified')
```

Next, we will set up the model and the training configuration, and launch the training.

```python
# Set up training configuration and train the model
cfg = get_cfg()
cfg.merge_from_file(model_zoo.get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
cfg.DATASETS.TRAIN = (dataset_train,)
cfg.DATASETS.TEST = ()
cfg.DATALOADER.NUM_WORKERS = 2
cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")
cfg.SOLVER.IMS_PER_BATCH = 8
cfg.SOLVER.BASE_LR = 0.005  # pick a good LR
cfg.SOLVER.MAX_ITER = 1000  # and a good number of iterations
cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(MetadataCatalog.get(dataset_train).thing_classes)

# Instantiate the trainer and train the model
os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
trainer = DefaultTrainer(cfg)
trainer.resume_or_load(resume=False)
setup_logger()
trainer.train()
```

Finally, we will evaluate the model using the built-in COCO evaluator.

```python
# Evaluate the model
cfg.MODEL.WEIGHTS = os.path.join(cfg.OUTPUT_DIR, "model_final.pth")
cfg.DATASETS.TEST = (dataset_val, )
evaluator = COCOEvaluator(dataset_val, cfg, False, output_dir="./output/")
val_loader = build_detection_test_loader(cfg, dataset_val)
inference_on_dataset(trainer.model, val_loader, evaluator)
```
