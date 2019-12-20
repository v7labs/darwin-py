# Darwin
Official library to manage datasets along with 
[V7 Darwin annotation platform](https://darwin.v7labs.com).

Darwin-py can be used as a python library or as a command line tool (CLI).
Main functions are (but not limited to):

- Client authentication
- Listing local and remote datasets
- Create/remove a dataset 
- Upload/download data to/from a remote dataset

Support tested for python 3.7.




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



---

## Usage as a Command Line Interface (CLI)

Once installed, `darwin` is accessible as a command line tool.
A useful way to navigate the CLI usage is through the help command `-h/--help` which will 
provide additional information for each command available. 


### Client Authentication 

To perform remote operations on Darwin you first need to authenticate.
This requires a [team-specific API-key](https://darwin.v7labs.com/?settings=api-keys).  
If you do not already have a Darwin account, you can [contact us](https://www.v7labs.com/contact) and we can set one up for you.

To start the authentication process, use:

```
$ darwin authenticate
```

You will be then prompted to insert the API-key, whether you want to set the corresponding team as 
default and finally the desired location on the local file system for the datasets of that team.
This process will create a configuration file at `~/.darwin/config.yaml`.
This file will be updated with future authentications for different teams.


### Listing local and remote datasets 

Lists a summary of local existing projects
```
$ darwin dataset local
NAME            IMAGES     SYNC_DATE         SIZE
mydataset       112025     yesterday     159.2 GB
```

Lists a summary of remote projects accessible by the current user.

```
$ darwin dataset remote
NAME                 IMAGES     PROGRESS
myteam/mydataset     112025        73.0%
```


### Create/remove a dataset 

To create an empty dataset remotely:

```
$ darwin dataset create test
Dataset 'test' (myteam/test) has been created.
Access at https://darwin.v7labs.com/datasets/579
``` 

Note that in this case `579` will be the dataset ID.
The dataset will be created in the team you're authenticated for.

To delete the project on the server:
```
$ darwin dataset remove test
About to delete myteam/test on darwin.
Do you want to continue? [y/N] y
```


### Upload/download data to/from a remote dataset 

Uploads data to an existing remote project.
It takes the dataset name and a single image (or directory) with images/videos to upload as 
parameters. 

The `-e/--exclude` argument allows to indicate file extension/s to be ignored from the data_dir. 
e.g.: `-e .jpg`

For videos, the frame rate extraction rate can be specified by adding `--fps <frame_rate>`

Supported extensions:
-  Video files: [`.mp4`, `.bpm`, `.mov` formats].
-  Image files [`.jpg`, `.jpeg`, `.png` formats].

```
$ darwin dataset push test /path/to/folder/with/images
100%|████████████████████████| 2/2 [00:01<00:00,  1.27it/s] 
```

Downloads a remote project, images and annotations, in the projects directory 
(specified in the authentication process [default: `~/.darwin/projects`]).

```
$ darwin dataset pull test 
Dataset myteam/test:versionname downloaded at /directory/choosen/at/authentication/time.
```


---
## Usage as a Python library

The framework is designed to be usable as a standalone python library.
Usage can be inferred from looking at the operations performed in `darwin/cli_functions.py`.
A minimal example to download a dataset is provided below and a more extensive one can be found in 
[darwin_demo.py](https://github.com/v7labs/darwin-py/blob/new_README/darwin_demo.py).

```python
from darwin.client import Client
from darwin.dataset.identifier import DatasetIdentifier

client = Client.local(team_slug="myteam") 
dataset_identifier = DatasetIdentifier.from_slug(dataset_slug="test", team_slug="myteam")
ds = client.get_remote_dataset(dataset_identifier=dataset_identifier)
ds.pull()    
```
