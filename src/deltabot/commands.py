
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
        short, long = parse_command_docstring(func)
        cmd_def = CommandDef(name, short=short, long=long, func=func)
        if name in self._cmd_defs:
            raise ValueError("command {!r} already registered".format(name))
        self._cmd_defs[name] = cmd_def
        self.logger.debug("registered new command {!r}".format(name))

    def unregister(self, name):
        return self._cmd_defs.pop(name)

    def dict(self):
        return self._cmd_defs.copy()

    @deltabot_hookimpl
    def deltabot_incoming_message(self, message, replies):
        if not message.text.startswith(CMD_PREFIX):
            return None
        parts = message.text.split(maxsplit=1)
        cmd_name = parts.pop(0)
        cmd_def = self._cmd_defs.get(cmd_name)
        if cmd_def is None:
            reply = "unknown command {!r}".format(cmd_name)
            self.logger.warn(reply)
            replies.add(text=reply)
            return True

        payload = parts[0] if parts else ""
        cmd = IncomingCommand(bot=self.bot, cmd_def=cmd_def, payload=payload, message=message)
        self.bot.logger.info("processing command {}".format(cmd))
        res = cmd.cmd_def.func(cmd)
        if res:
            replies.add(text=res)
            return True

    @deltabot_hookimpl
    def deltabot_init(self, bot):
        assert bot == self.bot
        self.register("/help", self.command_help)

    def command_help(self, command):
        """ reply with help message about available commands. """
        l = []
        l.append("**commands**")
        for c in self._cmd_defs.values():
            l.append("{}: {}".format(c.cmd, c.short))
        l.append("")
        pm = self.bot.plugins._pm
        plugins = [pm.get_name(plug) for plug, dist in pm.list_plugin_distinfo()]
        l.append("enabled plugins: {}".format(" ".join(plugins)))
        return "\n".join(l)


class CommandDef:
    """ Definition of a '/COMMAND' with args. """
    def __init__(self, cmd, short, long, func):
        if cmd[0] != CMD_PREFIX:
            raise ValueError("cmd {!r} must start with {!}".format(cmd, CMD_PREFIX))
        self.cmd = cmd
        self.long = long
        self.short = short
        self.func = func

    def __eq__(self, c):
        return c.__dict__ == self.__dict__


class IncomingCommand:
    """ incoming command request. """
    def __init__(self, bot, cmd_def, payload, message):
        self.bot = bot
        self.cmd_def = cmd_def
        self.payload = payload
        self.message = message

    def __repr__(self):
        return "<IncomingCommand {!r} payload={!r} msg={}>".format(
            self.cmd_def.cmd[0], self.payload, self.message.id)

    @property
    def args(self):
        return self.payload.split()


def parse_command_docstring(func):
    description = func.__doc__
    if not description:
        raise ValueError("command {!r} needs to have a docstring".format(func))

    lines = description.strip().split("\n")
    return lines.pop(0), "\n".join(lines).strip()
