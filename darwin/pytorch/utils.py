import os
import torch
import numpy as np
import matplotlib.pyplot as plt
import json
from pycocotools import mask as coco_mask
from pathlib import Path
from tqdm import tqdm

from darwin.client import Client

from PIL import Image
try:
    import accimage
except ImportError:
    accimage = None


def load_pil_image(path):
    '''
    Loads a PIL image and converts it into RGB.

    Input: path to the image file
    Output: PIL's Image
    '''
    pic = Image.open(path)
    if pic.mode == "RGB":
        pass
    elif pic.mode in ("CMYK", "RGBA"):
        pic = pic.convert('RGB')
    elif pic.mode == "I":
        img = (np.divide(np.array(pic, np.int32), 2**16-1)*255).astype(np.uint8)
        pic = Image.fromarray(np.stack((img, img, img), axis=2))
    elif pic.mode == "I;16":
        img = (np.divide(np.array(pic, np.int16), 2**8-1)*255).astype(np.uint8)
        pic = Image.fromarray(np.stack((img, img, img), axis=2))
    elif pic.mode == "L":
        img = np.array(pic).astype(np.uint8)
        pic = Image.fromarray(np.stack((img, img, img), axis=2))
    else:
        raise TypeError(f"unsupported image type {pic.mode}")
    return pic


def _is_pil_image(img):
    if accimage is not None:
        return isinstance(img, (Image.Image, accimage.Image))
    else:
        return isinstance(img, Image.Image)


def convert_polygon_to_mask(segmentations, height, width):
    '''
    Converts a polygon represented as a sequence of coordinates into a mask.

    Input: list of float values -> [x1, y1, x2, y2, ..., xn, yn]
    Output: PyTorch's tensor
    '''
    masks = []
    for polygons in segmentations:
        rles = coco_mask.frPyObjects(polygons, height, width)
        mask = coco_mask.decode(rles)
        if len(mask.shape) < 3:
            mask = mask[..., None]
        mask = torch.as_tensor(mask, dtype=torch.uint8)
        mask = mask.any(dim=2)
        masks.append(mask)
    if masks:
        masks = torch.stack(masks, dim=0)
    else:
        masks = torch.zeros((0, height, width), dtype=torch.uint8)
    return masks


def convert_polygon_to_sequence(polygon):
    '''
    Converts a sequence of dictionaries of (x,y) into an array of coordinates.

    Input: list of dictionaries -> [{x: x1, y:y1}, ..., {x: xn, y:yn}]
    Output: list of float values -> [x1, y1, x2, y2, ..., xn, yn]
    '''
    path = []
    if len(polygon) == 0:
        return path
    elif isinstance(polygon[0], dict):
        for e in polygon:
            path.append(e['x'])
            path.append(e['y'])
        return path
    else:
        return polygon


def polygon_area(x, y):
    '''
    Returns the area of the input polygon, represented with two numpy arrays
    for x and y coordinates.
    '''
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def extract_classes(files):
    classes = {}
    idx_to_classes = {}
    for i, fname in enumerate(files):
        with open(fname) as f:
            d = json.load(f)
            idx_to_classes[i] = []
            for a in d["annotations"]:
                cls_name = a["name"]
                try:
                    classes[cls_name].add(i)
                except KeyError:
                    classes[cls_name] = set([i])
                if cls_name not in idx_to_classes[i]:
                    idx_to_classes[i].append(cls_name)
    return classes, idx_to_classes


def fetch_darwin_dataset(db_name, client=None, val_perc=0.1, test_perc=0, image_status="done",
                         force_resplit=False, split_seed=None, **kwargs):
    if client is None:
        client = Client.default()

    # Get data
    local_datasets = {dataset.slug: dataset for dataset in client.list_local_datasets()}
    if db_name in local_datasets:
        dataset = local_datasets[db_name]
    else:
        remote_datasets = [dataset.slug for dataset in client.list_remote_datasets()]
        if db_name in remote_datasets:
            dataset = client.get_remote_dataset(slug=db_name)
            progress, _count = dataset.pull(image_status=image_status)
            with tqdm(total=_count, desc=f"Downloading dataset {db_name}") as pbar:
                for _ in progress():
                    pbar.update()
        else:
            raise ValueError(f"could not find dataset {db_name}")

    # Find annotations and create folders
    root = Path(client.project_dir) / db_name
    annot_path = root / "annotations"
    annot_files = [f for f in annot_path.glob('*.json')]
    num_images = len(annot_files)
    lists_path = root / "lists"
    if not lists_path.exists():
        os.makedirs(lists_path)

    # Extract classes
    fname = lists_path / "classes.txt"
    if not fname.exists():
        # Extract list of classes
        classes, idx_to_classes = extract_classes(annot_files)
        classes_names = [k for k in classes.keys()]
        classes_names.insert(0, '__background__')
        with open(lists_path / 'classes.txt', 'w') as f:
            for c in classes_names:
                f.write(f"{c}\n")

    # Create split
    split_id = f"split_val{val_perc}_test{test_perc}"
    split_path = lists_path / split_id
    if not split_path.exists() or force_resplit:
        os.makedirs(split_path)
        num_train = int(num_images * (1 - (val_perc + test_perc)))
        num_test = int(num_images * test_perc)
        num_val = num_images - num_train - num_test

        indices = np.random.permutation(num_images)
        train_idx = indices[:num_train]
        val_idx = indices[num_train:num_train+num_val]
        test_idx = indices[num_train+num_val:]

        # Write files
        with open(lists_path / 'train.txt', 'w') as f:
            for i in train_idx:
                f.write(f"{annot_files[i].stem}\n")
        if num_val > 0:
            with open(lists_path / 'val.txt', 'w') as f:
                for i in val_idx:
                    f.write(f"{annot_files[i].stem}\n")
        if num_test > 0:
            with open(lists_path / 'test.txt', 'w') as f:
                for i in test_idx:
                    f.write(f"{annot_files[i].stem}\n")

    return root, split_id


# VISUALIZATION
def visualize_mask_output(image, masks, classes, colors, threshold=0.5):
    W, H = image.size
    outmask = np.zeros((H, W, 4), dtype=np.uint8)
    for mask, c in zip(masks, classes):
        color = np.append(colors[c], 128)
        outmask[mask > threshold] = color

    outmask = Image.fromarray(outmask)
    image.paste(outmask, (0, 0), outmask)
    return image


def get_colors(n, name='hsv'):
    '''
    It return n distintc RGB colors using a mapping function that maps each index in 0, 1, ..., n-1 to a distinct
    RGB color; the keyword argument name must be a standard mpl colormap name.
    '''
    colors = list(map(plt.cm.get_cmap(name, n), range(n)))
    colors = list(map(lambda c: (np.array(c[:3])*255).astype(np.uint8), colors))
    return colors
