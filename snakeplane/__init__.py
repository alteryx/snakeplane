"""Snakeplane Alteryx Designer Python SDK Abstraction Layer."""

import lazy_import

from snakeplane.version import __version__

lazy_import.lazy_module("numpy")
lazy_import.lazy_module("pandas")
