# Developing for `darwin-py`

`darwin-py` uses a `pyproject.toml` file, and manages it with `poetry`

- [Developing for `darwin-py`](#developing-for-darwin-py)
  - [Development environment](#development-environment)
  - [Basic poetry commands](#basic-poetry-commands)
    - [Add a package to general dependencies:](#add-a-package-to-general-dependencies)
    - [Add a package to one of the extras groups](#add-a-package-to-one-of-the-extras-groups)
    - [Add a package to the poetry dev dependencies](#add-a-package-to-the-poetry-dev-dependencies)
  - [The `pyproject.toml` file](#the-pyprojecttoml-file)


## Development environment

You can either:
* Install a `poetry` environment, and work with that, or
* Install `darwin-py` using `pip` from Pypi.org, and make your own arrangements for debugging.

The recommended setup is to install poetry, and use this to setup a dev environment:

```sh
$ python --version  # must be 3.9 or greater for development tools
$ pip install poetry
$ poetry install --extras "test ml medical dev" -G dev
```

This creates a `virtualenv` for the project.  If you prefer, you can use `venv` by running this command before `poetry install`:

```sh
$ python -m venv .venv
```

You can give it a different name if you wish, but the name `.venv` is pre-ignored in the `.gitignore` file.


## Basic poetry commands

### Add a package to general dependencies:
```sh
$ poetry add [PACKAGENAME]
```


### Add a package to one of the extras groups

(these are those that are used in `pip install darwinpy[option]` type commands - ours are `test`, `ml`, `medical`, and `dev` - `dev` is for developers who don't want to use poetry - so they can install using `pip`)

```sh
$ poetry add [PACKAGENAME] --extras="extra group names"
```


Packages added this way will be installable with `pip` once a release has been made to PyPi.


### Add a package to the poetry dev dependencies

```sh
$ poetry add [PACKAGENAME] -G groupname
```

Currently the only group is `dev` and contains dev tools for developers using `poetry`.  `poetry` groups have no effect on packaging, and things installed here will not be packaged.

## The `pyproject.toml` file

This was a necessary change for PEP-517, but also allows us a central place to add configuration.

Items in the `pyproject.toml` file that are grouped as `[tool.X]` are configuration settings for specific tools on the system.

For example, settings for `mypy` static type analyser, are in the `[tool.mypy]` group.

A plugin is installed that allows `flake8` to take its configuration from this file, even though usually it only works with `setup.cfg` and `.flake8`.