
from collections import OrderedDict
from typing import Callable, List, Tuple

from .commands import parse_command_docstring
from .hookspec import deltabot_hookimpl

_filters: List[Tuple[str, Callable]] = []


class Filters:
    def __init__(self, bot) -> None:
        self.bot = bot
        self.logger = bot.logger
        self._filter_defs = OrderedDict()
        self.bot.plugins.add_module('filters', self)

    def register(self, name: str, func: Callable) -> None:
        """ register a filter function that acts on each incoming non-system message.
        :param name: name of the filter
        :param func: function can accept 'bot', 'message' and 'replies' arguments.
        """
        short, long, args = parse_command_docstring(func, args=['message', 'replies', 'bot'])
        cmd_def = FilterDef(name, short=short, long=long, func=func, args=args)
        if name in self._filter_defs:
            raise ValueError('filter {!r} already registered'.format(name))
        self._filter_defs[name] = cmd_def
        self.logger.debug('registered new filter {!r}'.format(name))

    def unregister(self, name: str) -> Callable:
        """ unregister a filter function. """
        return self._filter_defs.pop(name)

    def dict(self) -> dict:
        return self._filter_defs.copy()

    @deltabot_hookimpl(trylast=True)
    def deltabot_incoming_message(self, message, replies) -> None:
        for name, filter_def in self._filter_defs.items():
            self.logger.debug("calling filter {!r} on message id={}".format(name, message.id))
            res = filter_def(message=message, replies=replies, bot=self.bot)
            if res is not None:
                break


class FilterDef:
    """ Definition of a Filter that acts on incoming messages. """
    def __init__(self, name, short, long, func, args) -> None:
        self.name = name
        self.short = short
        self.long = long
        self.func = func
        self.args = args

    def __eq__(self, c) -> bool:
        return c.__dict__ == self.__dict__

    def __call__(self, **kwargs):
        for key in list(kwargs.keys()):
            if key not in self.args:
                del kwargs[key]
        return self.func(**kwargs)


def filter_decorator(func: Callable = None, name: str = None) -> Callable:
    """Register decorated function as bot filter."""
    def _decorator(func):
        _filters.append((name or func.__name__, func))
        return func

    if func is None:
        return _decorator
    return _decorator(func)