# Command line  

## Authentication
To perform remote operations on Darwin you first need to authenticate.
Authentication requires a [team-specific API-key](https://darwin.v7labs.com/?settings=api-keys).  
If you do not already have a Darwin account, you can [contact us](https://www.v7labs.com/contact) and we can set one up for you.

To start the authentication process:

```sh
$ darwin authenticate
API key: ***********
Make example-team the default team? [y/N] y
Datasets directory [~/.darwin/datasets]: 
Authentication succeeded.
```

You will be then prompted to enter your API-key, whether you want to set the corresponding team as 
default and finally the desired location on the local file system for the datasets of that team.
This process will create a configuration file at `~/.darwin/config.yaml`.
This file will be updated with future authentications for different teams.

**Note** that the API key rights selected when requesting the key determine which of the following commands are allowed. If the key has insufficient permissions for an action an error will be shown `Insufficient permissions` or `Invalid API key`. 

## Datasets
A central part of Darwin are the datasets. They contain images/videos, annotation classes, instructions and annotations. In this documentation we will refer to a dataset as *remote* when it's hosted on Darwin, and *local* when a copy has been made locally. 

A dataset can either be referred by its name directly, but this can lead to ambiguity when authenticating with multiple teams (hence the use of default team), or by `team-name/dataset-name`. Team and Dataset names are slugified:

* lower case
* spaces is replaced with dash
* special characters are stripped

Datasets can generate a release by freezing all annotations made up to a certain point in time, this release will have a unique name using this format `team-name/dataset-name:version-name` See (Releases)[###Releases]

### Creating a dataset 
Creates a new remote dataset (hosted on Darwin):
```
$ darwin dataset create test
Dataset 'mydataset' (example-team/mydataset) has been created.
Access at https://darwin.v7labs.com/datasets/579
``` 

### List remote datasets
Lists all datasets for the default team
```
$ darwin dataset remote
NAME                       IMAGES     PROGRESS
example-team/mydataset     112025        73.0%
example-team/fg-removal      3000        42.0%
```

Use the `-t` flag to specify a different team

```
$ darwin dataset remote -t other-team
NAME                       IMAGES     PROGRESS
other-team/ct-scans           450        100.0%
```

### List remote files
Lists all files in a remote dataset, can optional by filtered by file status and/or foldername. 
Allowed statuses: `new`, `annotate`, `review`, `complete`, `archived`

```
$ darwin dataset files example-team/mydataset 
test1.png complete
test2.png complete
test3.png annotate
```

```
$ darwin dataset files example-team/mydataset --path outdoors
test1.png complete
```

```
$ darwin dataset files example-team/mydataset --status complete
test1.png complete
test2.png complete
```

Add `--only-filenames` to only list the filename.

### Set file status
Allows to set the status of a file in a dataset. Allowed statuses are: `archived` and `restore-archived` (More will be added soon).

```
$ darwin dataset set-file-status v7/my-new-dataset archived 00000010.jpg
```

This can be used in conjunction with `darwin dataset files`, for example:
```
$ darwin dataset set-file-status v7/my-new-dataset archived $(darwin dataset files v7/my-new-dataset --status error --only-filenames)
```


### List local datasets
Local datasets are datasets that have been downloaded, 
```
$ darwin dataset local
NAME                                                   IMAGES     SYNC_DATE         SIZE
example-team/mydataset                                    999        May 25     150.2 MB
other-team/ct-scans                                       450        May 20     500.1 MB
```

### Uploading images/videos

For images and videos
```
$ darwin dataset push my-team/test /path/to/folder/with/images
100%|████████████████████████| 2/2 [00:01<00:00,  1.27it/s] 
```

Specifying framerate for videos
```
$ darwin dataset push my-team/test --fps 2 my_video.mp4
100%|████████████████████████| 1/1 [00:01<00:00,  1.27it/s] 
```

The `-e/--exclude` argument allows to indicate file extension/s to be ignored from the data_dir. 
e.g.: `-e .jpg`

For videos, the frame rate extraction rate can be specified by adding `--fps <frame_rate>`

Supported extensions:

-  Video files: [`.mp4`, `.bpm`, `.mov` formats].
-  Image files [`.jpg`, `.jpeg`, `.png` formats].

There is also an optional `--path` flag to move the uploaded files into the specified directory.
```
$ darwin dataset push my-team/test --path animals/cats cat1.png cat2.png
100%|████████████████████████| 1/2 [00:01<00:00,  2.42it/s] 
```


### Releases
To download data from a dataset, a release first needs to be created. Several releases can be kept locally at the same time, images are shared between the releases to reduce disk usage. 

```
/dataset_directory      # by default ~/.darwin/datasets
   /team-name
       /dataset-name
            /images     # shared between all releases
                1.png
                2.png
                3.png
            /releases
                /latest # symlink to the latest release (v3)
                /v3
                    1.json
                    2.json
                    3.json
                /v2
                    1.json
                    2.json
                /v1
                    1.json

```

#### Create a new release
```
$ darwin dataset export test 0.1
Dataset test successfully exported to example-team/test:0.1
```

#### List all releases 
```
$ darwin dataset releases example-team/my-new-dataset
NAME                                    IMAGES     CLASSES                   EXPORT_DATE
example-team/my-new-dataset:0.4             23           9     2020-05-11 14:48:25+00:00
example-team/my-new-dataset:0.2              1           8     2020-04-28 23:50:56+00:00
example-team/my-new-dataset:0.1             22           7     2020-04-17 09:57:22+00:00
```

#### Download a release 
```
$ darwin dataset pull example-team/my-new-dataset:0.1
100%|███████████████████████████| 100/100 [00:20<00:00,  7.18it/s]
Dataset example-team/my-new-dataset:0.4 downloaded at ~/.darwin/datasets/example-team
```

Note that if this was the latest release for this dataset, then this release can also be referred to it via `:latest` for local operations.

### Path to dataset
A convenient command to find a dataset on the local filesystem (if downloaded)
```
$ darwin dataset path example-team/my-new-dataset
/Users/me/.darwin/datasets/example-team/my-new-dataset
```

### Delete a remote dataset
This goes without saying, but be careful when deleting datasets. Their data will be cleared from Darwin's servers and unrecoverable after a couple of days. 
```
$ darwin dataset remove test
About to delete example-team/test on darwin.
Do you want to continue? [y/N] y
```

### Import annotations
If you want to bootstrap your dataset by importing already existing annotations, first make sure that all the images are already uploaded. Then ensure that the annotations are in one of the following formats [PascalVoc, COCO, CSV Tags]. 

```
$ darwin dataset import example-team/test pascal_voc sample_voc.xml
Fetching remote file list...
Fetching remote class list...
Retrieving local annotations ...
1 annotation file(s) found.
1 file(s) are missing from the dataset
        imports/sample_voc.xml: '12.png'
Do you want to continue? [y/N] y
0 classes are missing remotely.
```

There are few things going on here:

* first darwin-py tries to match each file in the import against files in the dataset, if that fails it will warn us and allow the operation to be cancelled. 
* then annotation classes are matched (exact name + type). If they are missing remotely darwin-py will prompt asking if it's allowed to create them.
* finally all the annotations are uploaded. 

**Note** In the current version, old annotations are deleted before the imports are applied. 

### Convert annotations

```
$ darwin dataset convert v7/my-new-dataset:standard coco output_directory
```

This converts the downloaded annotations from the darwin format to an external format. Currently supported: [COCO, CVAT, Pascal VOC]

**Note** Some annotations types are not valid for some formats, when that happens the annotation is simply dropped. 
