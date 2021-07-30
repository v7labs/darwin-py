import setuptools

with open("README.md", "rb") as f:
    long_description = f.read().decode("utf-8")

setuptools.setup(
    name="darwin-py",
    author="V7",
    author_email="info@v7labs.com",
    description="Library and command line interface for darwin.v7labs.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/v7labs/darwin-py",
    install_requires=[
        "argcomplete",
        "dataclasses",
        "humanize",
        "numpy",
        "pillow",
        "pyyaml>=5.1",
        "requests",
        "requests_toolbelt",
        "responses",
        "rich",
        "upolygon==0.1.6",
    ],
    packages=[
        "darwin",
        "darwin.importer",
        "darwin.dataset",
        "darwin.torch",
        "darwin.exporter",
        "darwin.importer.formats",
        "darwin.exporter.formats",
    ],
    entry_points={"console_scripts": ["darwin=darwin.cli:main"]},
    classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: MIT License"],
    python_requires=">=3.6",
)
