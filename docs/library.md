# Library

A central concept to `darwin-py` is the client object. It is authenticated with an API key and then used to create a Dataset Object (high level access) or diretly communicate with Darwin (low level access). 

Simple example
```python

client = Client.local() # use the configuration in ~/.darwin/config.yaml
dataset = client.get_remote_dataset("example-team/test")
dataset.pull() # downloads annotations and images for the latest exported version
```

## Creating the client
There are two ways of creating a Client object, directly from an API key

```python
from darwin.client import Client
client = Client.from_api_key("DHMhAWr.BHucps-tKMAi6rWF1xieOpUvNe5WzrHP")
```

or via the local configuration `~/.darwin/config.yaml` (see [command line authentication](commandline.md#Authentication))

```python
from darwin.client import Client
client = Client.local()
```

If the API key is invalid (malformed or archived) a `darwin.exceptions.InvalidLogin` will be raised.

## Find a remote dataset
```python
dataset = client.get_remote_dataset("example-team/test")
```
If the team isn't valid, `darwin.exceptions.InvalidTeam` will be raised.
If the dataset cannot be accessed, `darwin.exception.NotFound` will be raised. 
