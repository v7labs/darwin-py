import re
from pathlib import Path

import setuptools

with open(Path(__file__).parent / "darwin" / "version" / "__init__.py", "r") as f:
    content = f.read()
    # from https://www.py4u.net/discuss/139845
    version = re.search(r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]', content).group(1)  # type: ignore

with open("README.md", "rb") as f:
    long_description = f.read().decode("utf-8")

setuptools.setup(
    name="darwin-py",
    version=version,
    author="V7",
    author_email="info@v7labs.com",
    description="Library and command line interface for darwin.v7labs.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/v7labs/darwin-py",
    setup_requires=["wheel", "setuptools"],
    install_requires=[
        "argcomplete",
        "dataclasses;python_version<'3.7'",
        "humanize",
        "numpy<=1.23.0",
        "pillow",
        "pyyaml>=5.1",
        "requests",
        "rich",
        "upolygon==0.1.8",
        "jsonschema>=4.0.0",
        "deprecation",
        "pydantic",
        "ujson",
        "orjson",
    ],
    extras_require={
        "test": ["responses", "pytest", "pytest-describe", "scikit-learn"],
        "dev": ["black", "flake8", "isort", "mypy", "responses", "pytest", "pytest-describe", "scikit-learn"],
        "ml": ["scikit-learn", "torch", "torchvision"],
        "medical": ["nibabel", "connected-components-3d"],
    },
    packages=[
        "darwin",
        "darwin.importer",
        "darwin.dataset",
        "darwin.torch",
        "darwin.exporter",
        "darwin.importer.formats",
        "darwin.exporter.formats",
        "darwin.version",
    ],
    entry_points={"console_scripts": ["darwin=darwin.cli:main"]},
    classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: MIT License"],
    python_requires=">=3.6",
)
