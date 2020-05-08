# -*- coding: utf-8 -*-

from .hookspec import deltabot_hookimpl  # noqa
from .bot import DeltaBot  # noqa

from pkg_resources import get_distribution, DistributionNotFound
try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    __version__ = "0.0.0.dev0-unknown"
