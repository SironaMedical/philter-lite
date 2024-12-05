"""Confirm that project metadata is set correctly."""

import os
import sys
from typing import Any, Mapping

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib


import philter_lite

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PYPROJECT_TOML_PATH = os.path.join(TESTS_DIR, "..", "pyproject.toml")

with open(PYPROJECT_TOML_PATH, "rb") as pyproject_file:
    pyproject_toml: Mapping[str, Any] = tomllib.load(pyproject_file)


def test_version():
    """Ensure package version is reported correctly as metadata of the package itself.

    Manually asserted in the package __init__.py.
    """
    assert philter_lite.__version__ == pyproject_toml["tool"]["poetry"]["version"]
