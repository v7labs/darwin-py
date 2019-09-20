# Darwin
Official library to manage datasets along with v7 Darwin annotation platform [https://darwin.v7labs.com](https://darwin.v7labs.com).

Support tested for python3.7.

## Installation

### Standard

```
pip install darwin-py
```
You can now type `darwin` in your terminal and access the command line interface.

### Development
After cloning the repository:

```
pip install --editable .
```

## Usage

Darwin can be used as a python library or as a command line tool.
Main functions are:

- Authentication
- Listing local and remote a dataset
- Creating and removing a dataset 
- Uploading data to a remote dataset
- Download data locally from a remote dataset

### As a library

Darwin can be used as a python library to download / upload and list datasets.

To access darwin you first need to authenticate, this can be done once through the cli (see the `Authentication`) or directly in python, see the example below.

#### Authentication 
Authenticate without ~/.darwin/config.yaml file (which gets generated with CLI)

```python
from darwin.client import Client

client = Client.login(email="simon@v7labs.com", password="*********")
```

#### Local projects
Print a list of local existing projects

```python
from darwin.client import Client

client = Client.default()
for dataset in client.list_local_datasets():
    print(dataset.slug, dataset.image_count)
```

#### Remote projects
Print a list of remote projects accessible by the current user.

```python
from darwin.client import Client

client = Client.default()
for dataset in client.list_remote_datasets():
    print(dataset.slug, dataset.image_count)
```

#### Upload data to a [remote] project (images/videos)

Uploads data to an existing remote project.
It takes the dataset slug and a list of file names of images/videos to upload as parameters.

```python
from darwin.client import Client

client = Client.default()
dataset = client.get_remote_dataset(slug="example-dataset")
progress = dataset.upload_files(["test.png", "test.mp4"])
for _ in progress():
    print("file uploaded")
```

#### Pull a [remote] project

Downloads a remote project, images and annotations, in the projects directory (specified in the authentication process [default: ~/.darwin/projects]).
```python
from darwin.client import Client

client = Client.default()
dataset = client.get_remote_dataset(slug="example-dataset")
progress, _count = dataset.pull()
for _ in progress():
    print("file synced")
```

### Command line

`darwin` is also accessible as a command line tool.


#### Authentication
A username (email address) and password is required to authenticate. If you do not already have a Darwin account, register for free at [https://darwin.v7labs.com](https://darwin.v7labs.com).
```
$ darwin authenticate
Username (email address): simon@v7labs.com
Password: *******
Project directory [~/.darwin/projects]: 
Projects directory created /Users/simon/.darwin/projects
Authentication succeeded.
```

#### Create a new dataset (from images/videos)
Creates an empty dataset remotely.

```
$ darwin create example-dataset
Dataset 'example-project' has been created.
Access at https://darwin.v7labs.com/datasets/example-project
```

#### Upload data to a [remote] project (images/videos)
Uploads data to an existing remote project. It takes the project name and a single image (or directory) with images/videos to upload as parameters. 

The `-e/--exclude` argument allows to indicate file extension/s to be ignored from the data_dir.

For videos, the frame rate extraction rate can be specified by adding `--fps <frame_rate>`

To recursively upload all files in a directory tree add the `-r` flag.

Supported extensions:
-  Video files: [`.mp4`, `.bpm`, `.mov` formats].
-  Image files [`.jpg`, `.jpeg`, `.png` formats].

```
$ darwin upload example-dataset -r path/to/images
Uploading: 100%|########################################################| 3/3 [00:01<00:00,  2.29it/s]
```

#### Remote projects
Lists a summary of remote projects accessible by the current user.

```
$ darwin remote
NAME                 IMAGES     PROGRESS     ID
example-project           3         0.0%     89
```

#### Pull a [remote] project
Downloads a remote project, images and annotations, in the projects directory (specified in the authentication process [default: `~/.darwin/projects`]).

```
$ darwin pull example-project
Pulling project example-project:latest
Downloading: 100%|########################################################| 3/3 [00:03<00:00,  4.11it/s]
```

#### Local projects
Lists a summary of local existing projects
```
$ darwin local
NAME                IMAGES     SYNC DATE          SIZE
example-project          3         today      800.2 kB
```

#### Remove projects
Removes a local project, located under the projects directory.

```
$ darwin remove example-project
About to deleting example-project locally.
Do you want to continue? [y/N] y
```

To delete the project on the server add the `-r` /`--remote` flag
```
$ darwin remove example-project --remote
About to deleting example-project on darwin.
Do you want to continue? [y/N] y
```

## Table of Arguments

| parser          | parameter                | type               | required  |
| --------------- | ------------------------ | -----------------  | --------- |
| `authenticate`  |                          |                    |           |
| `team`          |                          |                    |           |
|                 | `team_name`              | str                | False     |
|                 | `-l`, `--list`           |                    | False     |
| `create`        | `project_name`           | str                | True      |
| `local`         |                          |                    |           |
| `path`          | `project_name`           | str/int            | True      |
| `pull`          | `project_name`           | str/int            | True      |
| `remote`        |                          | str                |           |
| `remove`        | `project_name`           | str                | True      |
|                 | `-r` `--remote`          | str                | True      |
| `url`           | `project_name`           | str                |           |
| `upload`        | `project_name`           | str                | True      |
|                 | `data_dir`               | str                | True      |
|                 | `-e`, `--exclude`        | str                |           |
|                 | `--fps`                  | int                |           |
|                 | `-r`, `--recursive`      |                    |           |
