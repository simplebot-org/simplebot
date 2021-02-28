
from collections import OrderedDict
from typing import Callable

from .commands import parse_command_docstring
from .hookspec import deltabot_hookimpl


class Filters:
    def __init__(self, bot) -> None:
        self.bot = bot
        self.logger = bot.logger
        self._filter_defs = OrderedDict()
        self.bot.plugins.add_module("filters", self)

    def register(self, name: str, func: Callable) -> None:
        """ register a filter function that acts on each incoming non-system message. """
        short, long = parse_command_docstring(func, args=["message", "replies"])
        cmd_def = FilterDef(name, short=short, long=long, func=func)
        if name in self._filter_defs:
            raise ValueError("filter {!r} already registered".format(name))
        self._filter_defs[name] = cmd_def
        self.logger.debug("registered new filter {!r}".format(name))

    def unregister(self, name: str) -> Callable:
        """ unregister a filter function. """
        return self._filter_defs.pop(name)

    def dict(self) -> dict:
        return self._filter_defs.copy()

    @deltabot_hookimpl(trylast=True)
    def deltabot_incoming_message(self, message, replies) -> None:
        for name, filter_def in self._filter_defs.items():
            self.logger.debug("calling filter {!r} on message id={}".format(name, message.id))
            res = filter_def.func(message=message, replies=replies)
            if res is not None:
                break


class FilterDef:
    """ Definition of a Filter that acts on incoming messages. """
    def __init__(self, name, short, long, func) -> None:
        self.name = name
        self.short = short
        self.long = long
        self.func = func

    def __eq__(self, c) -> bool:
        return c.__dict__ == self.__dict__
