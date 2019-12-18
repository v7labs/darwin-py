# Darwin
Official library to manage datasets along with 
[V7 Darwin annotation platform](https://darwin.v7labs.com).

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




## Usage

Darwin can be used as a python library or as a command line tool.
Main functions are:

- Client authentication
- Listing local and remote datasets
- Create/remove a dataset 
- Upload/download data to/from a remote dataset

---

### As a Command Line Interface (CLI)

`darwin` is accessible as a command line tool.
An important tool to navigate the CLI usage is trough the help command `-h/--help` which will 
provide additional information for each command available. 


#### Client Authentication 

To access darwin you first need to authenticate.
This requires an team-specific [API-key](https://darwin.v7labs.com/?settings=api-keys).  
If you do not already have a Darwin account, you can [register for free](https://darwin.v7labs.com).

To start the authentication process, use:

```
$ darwin authenticate
```

You will be them prompted to insert the API-key, whether you want to set the corresponding team as 
default and finally the desired location on the file system for the datasets of that team.
This process will create a configuration in `~/.darwin/config.yaml`.
This file will be updated with future authentications. 


#### Listing local and remote datasets 

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


#### Create/remove a dataset 

To creates an empty dataset remotely:

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


#### Upload/download data to/from a remote dataset 

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
TODO update output
```




### As a Python Library

The framework is designed to be usable as a standalone python library.
Usage can be inferred from looking at the operations performed in `cli_functions.py`.
A minimal example to download a datset can be found in the 
[demo](https://github.com/v7labs/darwin-py/blob/new_README/darwin_demo.py).



