# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Match, Optional

sys.path.insert(0, os.path.abspath("../darwin/"))


# -- Project information -----------------------------------------------------

project: str = "darwin-py"
copyright: str = "MIT License"
author: str = "V7"

# The full version, including alpha/beta/rc tags
release: str = "0.0.0"

with open(Path(__file__).parent.parent / "darwin" / "__init__.py", "r") as f:
    # from https://www.py4u.net/discuss/139845
    content: str = f.read()
    search_result: Optional[Match[str]] = re.search(r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]', content)
    if search_result:
        release = search_result.group(1)

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions: List[str] = ["sphinx.ext.viewcode", "sphinx.ext.napoleon", "sphinx.ext.autodoc"]

# Add any paths that contain templates here, relative to this directory.
templates_path: List[str] = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns: List[str] = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme: str = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path: List[str] = ["_static"]

# This is a hack so we can have the left menu bar expand automatically upon opening a page.
# This hack is needed because of a bug in Sphinx:
# https://github.com/readthedocs/sphinx_rtd_theme/issues/455
#
# If one day the bug gets fixed, then `html_js_files` and `html_theme_options` can be removed
# as well as the files/directories they rely on.
html_js_files: List[str] = ["js/custom.js"]
html_theme_options: Dict[str, Any] = {
    "collapse_navigation": False,
}
