#!/usr/bin env python3

# TODO: refactor as needed

python -m pip install --upgrade pip
pip install poetry
poetry install --all-extras --no-interaction --no-root
pip install wheel
pip install --upgrade setuptools
pip install --editable ".[test,ml,medical,dev]"
pip install torch torchvision
pip install -U sphinx
# Locking mistune version so m2r works. More info on issue:
# https://github.com/miyakogi/m2r/issues/66
pip install mistune==0.8.4    # TODO: Mistune is now at version 3, so this is quite old, look into upgrading
pip install m2r               # TODO: m2r is deprecated.  Find alternative.
pip install sphinx_rtd_theme