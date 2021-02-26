# -*- coding: utf-8 -*-

from .hookspec import deltabot_hookimpl  # noqa
from .bot import DeltaBot  # noqa

__version__ = '0.11.0'

# for nice access via deltabot.hookimpl
hookimpl = deltabot_hookimpl
