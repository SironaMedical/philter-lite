from importlib import resources
from typing import Any, MutableMapping

import toml

from philter_lite import filters


def load_regex_db() -> MutableMapping[str, Any]:
    return toml.loads(resources.read_text(filters, "regex.toml"))


def load_regex_context_db() -> MutableMapping[str, Any]:
    return toml.loads(resources.read_text(filters, "regex_context.toml"))


def load_set_db() -> MutableMapping[str, Any]:
    return toml.loads(resources.read_text(filters, "set.toml"))


regex_db: MutableMapping[str, Any] = load_regex_db()
regex_context_db: MutableMapping[str, Any] = load_regex_context_db()
set_db: MutableMapping[str, Any] = load_set_db()
