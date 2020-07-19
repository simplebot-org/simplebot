
from collections import OrderedDict

from . import deltabot_hookimpl
from .commands import parse_command_docstring


class Filters:
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self._filter_defs = OrderedDict()
        self.bot.plugins.add_module("filters", self)

    def register(self, name, func):
        short, long = parse_command_docstring(func, args=["message", "replies"])
        cmd_def = FilterDef(name, short=short, long=long, func=func)
        if name in self._filter_defs:
            raise ValueError("filter {!r} already registered".format(name))
        self._filter_defs[name] = cmd_def
        self.logger.debug("registered new filter {!r}".format(name))

    def unregister(self, name):
        return self._filter_defs.pop(name)

    def dict(self):
        return self._filter_defs.copy()

    @deltabot_hookimpl
    def deltabot_incoming_message(self, message, replies):
        for name, filter_def in self._filter_defs.items():
            self.logger.debug("calling filter {!r} on message id={}".format(name, message.id))
            res = filter_def.func(message=message, replies=replies)
            assert res is None


class FilterDef:
    """ Definition of a Filter that acts on incoming messages. """
    def __init__(self, name, short, long, func):
        self.name = name
        self.short = short
        self.long = long
        self.func = func

    def __eq__(self, c):
        return c.__dict__ == self.__dict__
