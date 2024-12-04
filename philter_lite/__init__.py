"""The philter_lite package."""
from importlib import metadata

from philter_lite.coordinate_map import CoordinateMap
from philter_lite.filters import Filter, filter_from_dict, load_filters
from philter_lite.philter import detect_phi

# Writers
from .asterisk import transform_text_asterisk
from .i2b2 import transform_text_i2b2

__all__ = [
    "CoordinateMap",
    "Filter",
    "filter_from_dict",
    "load_filters",
    "detect_phi",
    "transform_text_asterisk",
    "transform_text_i2b2",
]

_DISTRIBUTION_METADATA = metadata.metadata("philter_lite")

__author__ = _DISTRIBUTION_METADATA["Author"]
__email__ = _DISTRIBUTION_METADATA["Author-email"]
__version__ = _DISTRIBUTION_METADATA["Version"]
