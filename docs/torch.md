# PyTorch bindings

This module includes some functionality to import your datasets ready to be plugged into Pytorch's `DataLoader`. For this, you can use the `get_dataset` function:

```python
get_dataset("/PATH/TO/YOUR/LOCAL/DATASET", DATASET_TYPE [, PARTITION, SPLIT_TYPE, RELEASE_NAME, TRANSFORMS])
```

Here is an example of how to load the `bird-species` dataset ready to be used in a instance segmentation task using `"instance_segmentation"` as `dataset_type` (alternatively you can use `"classification"` or `"semantic_segmentation"` for those other tasks):

```python
from darwin.torch import get_dataset

dataset_path = "/datasets/v7-demo/bird-species"
db = get_dataset(dataset_path, dataset_type="instance_segmentation")
```

You can use this function in combination with `split_dataset()` to create and load different partitions:

```python
from darwin.dataset.utils import split_dataset
from darwin.torch import get_dataset
import darwin.torch.transforms as T

dataset_path = "/datasets/v7-demo/bird-species"
split_dataset(dataset_path, val_percentage=20, test_percentage=0)

trfs_train = T.Compose([T.RandomHorizontalFlip(), T.ToTensor()])
db_train = get_dataset(dataset_path, dataset_type="instance_segmentation", \
    partition="train", split_type="stratified", transform=trfs_train)

trfs_val = T.ToTensor()
db_val = get_dataset(dataset_path, dataset_type="instance_segmentation", \
    partition="val", split_type="stratified", transform=trfs_val)

print(db_train)
# Returns:
# InstanceSegmentationDataset():
#   Root: /datasets/bird-species
#   Number of images: 1528
#   Number of classes: 3
```


## Darwin :heart: Torchvision


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


device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')

# Get training dataset
trfs_train = T.Compose([T.RandomHorizontalFlip(), T.ToTensor()])
dataset = get_dataset("/datasets/v7-demo/bird-species", dataset_type="instance_segmentation",
                      partition="train", split_type="stratified", transform=trfs_train)
data_loader = torch.utils.data.DataLoader(dataset, batch_size=2, shuffle=True, num_workers=4, collate_fn=collate_fn)

# get the model using our helper function
num_classes = dataset.num_classes + 1 # number of classes in the dataset + background
model = get_instance_segmentation_model(num_classes)
model.to(device)

# construct an optimizer
params = [p for p in model.parameters() if p.requires_grad]
optimizer = torch.optim.SGD(params, lr=0.005, momentum=0.9, weight_decay=0.0005)
# and a learning rate scheduler
lr_scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.1)

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


## Darwin :heart: Detectron2

```python
import os
# import some common detectron2 utilities
from detectron2.utils.logger import setup_logger
from detectron2 import model_zoo
from detectron2.engine import DefaultTrainer
from detectron2.config import get_cfg
from detectron2.data import MetadataCatalog, DatasetCatalog, build_detection_test_loader
from detectron2.evaluation import COCOEvaluator, inference_on_dataset
# import darwin utilities
from darwin.dataset.utils import get_annotations, get_classes


def register_darwin_dataset(dataset_path, partition, split_type='stratified'):
    catalog_name = f"darwin_{os.path.basename(dataset_path)}_{partition}"
    classes = get_classes(dataset_path, annotation_type='polygon')
    DatasetCatalog.register(
        catalog_name,
        lambda partition=partition: list(get_annotations(dataset_path, partition, split_type=split_type))
    )
    MetadataCatalog.get(catalog_name).set(thing_classes=classes)
    return catalog_name


# Register both training and validation sets
dataset_path = '/datasets/v7-demo/bird-species'
dataset_train = register_darwin_dataset(dataset_path, 'train')
dataset_val = register_darwin_dataset(dataset_path, 'val')

# Set up training configuration and train the model
cfg = get_cfg()
cfg.merge_from_file(model_zoo.get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
cfg.DATASETS.TRAIN = (dataset_train,)
cfg.DATASETS.TEST = ()
cfg.DATALOADER.NUM_WORKERS = 2
cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")
cfg.SOLVER.IMS_PER_BATCH = 8
cfg.SOLVER.BASE_LR = 0.00025  # pick a good LR
cfg.SOLVER.MAX_ITER = 100  # and a good number of iterations
cfg.MODEL.ROI_HEADS.NUM_CLASSES = len(MetadataCatalog.get(dataset_train).thing_classes)

os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
trainer = DefaultTrainer(cfg)
trainer.resume_or_load(resume=False)
setup_logger()
trainer.train()

# Evaluate the model
cfg.MODEL.WEIGHTS = os.path.join(cfg.OUTPUT_DIR, "model_final.pth")
cfg.DATASETS.TEST = (dataset_val, )
evaluator = COCOEvaluator(dataset_val, cfg, False, output_dir="./output/")
val_loader = build_detection_test_loader(cfg, dataset_val)
inference_on_dataset(trainer.model, val_loader, evaluator)
```
