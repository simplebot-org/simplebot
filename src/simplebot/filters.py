from collections import OrderedDict
from typing import Callable, Dict, Set, Tuple

from .commands import parse_command_docstring
from .hookspec import deltabot_hookimpl

_filters: Set[Tuple[str, Callable, bool, bool]] = set()


class Filters:
    def __init__(self, bot) -> None:
        self.logger = bot.logger
        self._filter_defs: Dict[str, FilterDef] = OrderedDict()
        bot.plugins.add_module("filters", self)

    def register(
        self, name: str, func: Callable, tryfirst: bool = False, trylast: bool = False
    ) -> None:
        """register a filter function that acts on each incoming non-system message.
        :param name: name of the filter.
        :param func: function can accept 'bot', 'message' and 'replies' arguments.
        :param tryfirst: Set to True if the filter should be executed as
                         soon as possible.
        :param trylast: Set to True if the filter should be executed as
                        late as possible.
        """
        short, long, args = parse_command_docstring(
            func, args=["message", "replies", "bot"]
        )
        prio = 0 - tryfirst + trylast
        cmd_def = FilterDef(
            name, short=short, long=long, func=func, args=args, priority=prio
        )
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
    def deltabot_incoming_message(self, bot, message, replies) -> None:
        for name, filter_def in sorted(
            self._filter_defs.items(), key=lambda e: e[1].priority
        ):
            self.logger.debug(
                "calling filter {!r} on message id={}".format(name, message.id)
            )
            res = filter_def(message=message, replies=replies, bot=bot)
            assert res is None


class FilterDef:
    """ Definition of a Filter that acts on incoming messages. """

    def __init__(self, name, short, long, func, args, priority) -> None:
        self.name = name
        self.short = short
        self.long = long
        self.func = func
        self.args = args
        self.priority = priority

    def __eq__(self, c) -> bool:
        return c.__dict__ == self.__dict__

    def __call__(self, **kwargs):
        for key in list(kwargs.keys()):
            if key not in self.args:
                del kwargs[key]
        return self.func(**kwargs)


def filter_decorator(
    func: Callable = None,
    name: str = None,
    tryfirst: bool = False,
    trylast: bool = False,
) -> Callable:
    """Register decorated function as bot filter.

    Check documentation of method `simplebot.filters.Filters.register` to
    see all parameters the decorated function can accept.
    """

    def _decorator(func) -> Callable:
        _name = name or "{}.{}".format(func.__module__, func.__name__)
        _filters.add((_name, func, tryfirst, trylast))
        return func

    if func is None:
        return _decorator
    return _decorator(func)
