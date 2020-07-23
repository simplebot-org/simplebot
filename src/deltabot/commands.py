
import inspect
from collections import OrderedDict


from . import deltabot_hookimpl


CMD_PREFIX = '/'


class NotFound(LookupError):
    """Command was not found. """


class Commands:
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self._cmd_defs = OrderedDict()
        self.bot.plugins.add_module("commands", self)

    def register(self, name, func):
        """ register a command function that acts on each incoming non-system message.

        :param name: name of the command, example "/test"
        :param func: function that needs to accept 'command' and 'replies' arguments,
                     namely a :class:`deltabot.command.IncomingCommand`
                     and a :class:`deltabot.bot.Replies` object.
        """
        short, long = parse_command_docstring(func, args=["command", "replies"])
        for cand_name in iter_underscore_subparts(name):
            if cand_name in self._cmd_defs:
                raise ValueError("command {!r} fails to register, conflicts with: {!r}".format(
                                 name, cand_name))
        for reg_name in self._cmd_defs:
            if reg_name.startswith(name + "_"):
                raise ValueError("command {!r} fails to register, conflicts with: {!r}".format(
                                 name, reg_name))

        cmd_def = CommandDef(name, short=short, long=long, func=func)
        self._cmd_defs[name] = cmd_def
        self.logger.debug("registered new command {!r}".format(name))

    def unregister(self, name):
        """ unregister a command function by name. """
        return self._cmd_defs.pop(name)

    def dict(self):
        return self._cmd_defs.copy()

    @deltabot_hookimpl
    def deltabot_incoming_message(self, message, replies):
        if not message.text.startswith(CMD_PREFIX):
            return None
        args = message.text.split()
        payload = message.text.split(maxsplit=1)[1] if len(args) > 1 else ""
        orig_cmd_name = args.pop(0)

        parts = orig_cmd_name.split("_")
        while parts:
            cmd_name = "_".join(parts)
            cmd_def = self._cmd_defs.get(cmd_name)
            if cmd_def is not None:
                break
            newarg = parts.pop()
            args.insert(0, newarg)
            payload = (newarg + " " + payload).rstrip()
        else:
            reply = "unknown command {!r}".format(orig_cmd_name)
            self.logger.warn(reply)
            if not message.chat.is_group():
                replies.add(text=reply)
            return True

        cmd = IncomingCommand(bot=self.bot, cmd_def=cmd_def, message=message,
                              args=args, payload=payload)
        self.bot.logger.info("processing command {}".format(cmd))
        try:
            res = cmd.cmd_def.func(command=cmd, replies=replies)
        except Exception as ex:
            self.logger.exception(ex)
        else:
            assert res is None, res
        return True

    @deltabot_hookimpl
    def deltabot_init(self, bot):
        assert bot == self.bot
        self.register("/help", self.command_help)

    def command_help(self, command, replies):
        """ reply with help message about available commands. """
        l = []
        l.append("**commands**")
        for c in self._cmd_defs.values():
            l.append("{}: {}".format(c.cmd, c.short))
        l.append("")
        pm = self.bot.plugins._pm
        plugins = [pm.get_name(plug) for plug, dist in pm.list_plugin_distinfo()]
        l.append("enabled plugins: {}".format(" ".join(plugins)))
        replies.add(text="\n".join(l))


class CommandDef:
    """ Definition of a '/COMMAND' with args. """
    def __init__(self, cmd, short, long, func):
        if cmd[0] != CMD_PREFIX:
            raise ValueError("cmd {!r} must start with {!r}".format(cmd, CMD_PREFIX))
        self.cmd = cmd
        self.long = long
        self.short = short
        self.func = func

    def __eq__(self, c):
        return c.__dict__ == self.__dict__


class IncomingCommand:
    """ incoming command request. """
    def __init__(self, bot, cmd_def, args, payload, message):
        self.bot = bot
        self.cmd_def = cmd_def
        self.args = args
        self.payload = payload
        self.message = message

    def __repr__(self):
        return "<IncomingCommand {!r} payload={!r} msg={}>".format(
            self.cmd_def.cmd[0], self.payload, self.message.id)


def parse_command_docstring(func, args):
    description = func.__doc__
    if not description:
        raise ValueError("command {!r} needs to have a docstring".format(func))
    funcargs = set(inspect.getargs(func.__code__).args)
    for arg in args:
        if arg not in funcargs:
            raise ValueError("{!r} needs to accept {!r} argument".format(func, arg))

    lines = description.strip().split("\n")
    return lines.pop(0), "\n".join(lines).strip()


def iter_underscore_subparts(name):
    parts = name.split("_")
    while parts:
        yield "_".join(parts)
        parts.pop()
