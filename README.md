# Darwin
Official library to manage datasets along with v7 Darwin annotation platform ["https://darwin.v7labs.com"].

Support tested for python3.7.

## Installation
[Using `pip install`.] Create and enter an Anaconda [] python 3.7 environment:

```
conda create --name py37 python=3.7
conda activate py37
```

### Standard

```
python3.7 -m pip install git+https://github.com/v7labs/darwin-cli
```
You can now type `darwin` in your terminal and access the command line interface.

### Development
After cloning the repo:

```
python3.7 -m pip install --editable .
```

## Usage

### Authenticate
After installing darwin you first need to authenticate yourself against the server. 

If you do not have a darwin account signup for free at https://darwin.v7labs.com
```bash
$ darwin authenticate
Username (email address): simon@v7labs.com
Password: *******
Project directory [~/.darwin/projects]: 
Projects directory created /Users/simon/.darwin/projects
Authentication succeeded.
```

### As a library

Darwin can be used as a python library to download / upload and list datasets.

*Print out remote & local datasets*
```python
from darwin.client import Client

client = Client.default()

for dataset in client.list_remote_datasets():
    print(dataset.name, dataset.image_count)

for dataset in client.list_local_datasets():
    print(dataset.name, dataset.image_count)
```

*Upload files to a remote dataset*
```python
from darwin.client import Client

client = Client.default()
dataset = client.get_remote_dataset(slug="example-dataset")
progress = dataset.upload_files(["test.png", "test.mp4"])
for _ in progress:
    print("file uploaded")
```

*Sync remote dataset to local machine*
```python
from darwin.client import Client

client = Client.default()
dataset = client.get_remote_dataset(slug="example-dataset")
progress, _count = dataset.pull()
for _ in progress:
    print("file synced")
```

*Login without ~/.darwin/config.yaml file*
```python
from darwin.client import Client

client = Client.login(email="simon@v7labs.com", password="*********")
...
```


### Command line

`darwin` is also accessible as a command line tool.


### Authentication
It requires username (email address) and password. Please, register at ["https://darwin.v7labs.com"].
```
python3.7 -m darwin.cli authenticate
```

### Create a new project (from images/videos)
Creates an empty project remotely to which a dataset can be uploaded afterwards (see `upload`).

```
python3.7 -m darwin.cli create {my_project_name}
```

### Local projects
Lists a summary of local existing projects
```
python3.7 -m darwin.cli local
```

### Pull a [remote] project
Downloads a remote project --images and annotations (`.json`)-- in the projects directory (specified in the authentication process [default: `~/.darwin/projects`]).

```
python3.7 -m darwin.cli pull {my_project_name}
```

### Remote projects
Lists a summary of remote existing projects

```
python3.7 -m darwin.cli remote
```

### Remove [remote] projects
Removes (archives) a remote project. If the local flag `-l`/`--local` is added, it removes the local directory of the project, located under the projects directory (specified in the authentication process [default: `~/.darwin/projects`]).

```
python3.7 -m darwin.cli remote
```

### Upload data to a [remote] project (images/videos)
Uploads data to an existing remote project. It accepts `data_path` a single image/video file or a data folder with images and/or videos. The `-e/--exclude` argument allows to indicate file extension/s to be ignored from the data_dir.

When the "frames per second" argument is explicit `-fps`, it splits the video/s in that many images per second of recording.

Supported extensions:
    -  Video files: [`.mp4`, `.bpm`, `.mov` formats].
    -  Image files [`.jpg`, `.jpeg`, `.png` formats].

```
python3.7 -m darwin.cli upload {my_project_name} {my_data_dir}
python3.7 -m darwin.cli upload {my_project_name} {my_data_dir} -exclude {extensions_to_include}
```

### Project report 
Prints a summary of the project annotations.

```
python3.7 -m darwin.cli report {my_project_name}
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
