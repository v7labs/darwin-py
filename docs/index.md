# Darwin SDK and CLI
Official documentation of [darwin-py](https://github.com/v7labs/darwin-py/), for managing datasets and annotations on
[V7 Darwin](https://darwin.v7labs.com).

Typical use cases for Darwin include:

- Create/remove/list datasets
- Upload/download data to/from remote datasets
- Convert between annotations formats
- Direct integration with PyTorch DataLoaders (See [torch/README.md](darwin/torch/README.md))

Darwin-py can both be used from the [command line](commandline.md) and as a [python library](#usage-as-a-python-library).

## Installation
```bash
pip install darwin-py
```

Once installed, `darwin` will be available from the command line. 

**Note**: darwin-py has been tested for python >= 3.6, while older versions might work they are not supported. 

### PyTorch

To use Darwin's PyTorch dataloaders the `torch` extra package is needed:

```bash
pip install darwin-py[torch]
```
