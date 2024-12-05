import sys
from importlib.resources import as_file, files
from typing import Any, MutableMapping

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from philter_lite import filters


def _get_toml_from_filters(filename: str) -> MutableMapping[str, Any]:
    source = files(filters).joinpath(filename)
    with as_file(source) as path:
        with open(path, "rb") as toml_file:
            toml_data = tomllib.load(toml_file)
    return toml_data


def load_regex_db() -> MutableMapping[str, Any]:
    return _get_toml_from_filters("regex.toml")


def load_regex_context_db() -> MutableMapping[str, Any]:
    return _get_toml_from_filters("regex_context.toml")


def load_set_db() -> MutableMapping[str, Any]:
    return _get_toml_from_filters("set.toml")


regex_db: MutableMapping[str, Any] = load_regex_db()
regex_context_db: MutableMapping[str, Any] = load_regex_context_db()
set_db: MutableMapping[str, Any] = load_set_db()
