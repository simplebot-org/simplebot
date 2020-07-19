
from deltabot.hookspec import deltabot_hookimpl


@deltabot_hookimpl
def deltabot_init_parser(parser):
    parser.add_subcommand(db_set)
    parser.add_subcommand(db_get)
    parser.add_subcommand(db_list)


@deltabot_hookimpl
def deltabot_init(bot):
    bot.commands.register(name="/set", func=command_set)


def slash_scoped_key(key):
    i = key.find("/")
    if i == -1:
        raise ValueError("key {!r} does not contain a '/' scope delimiter")
    return (key[:i], key[i + 1:])


class db_get:
    """Get a low level setting."""

    def add_arguments(self, parser):
        parser.add_argument("key", type=slash_scoped_key, help="low level database key")

    def run(self, bot, args, out):
        scope, key = args.key
        res = bot.get(key, scope=scope)
        if res is None:
            out.fail("key {} does not exist".format("/".join(args.key)))
        else:
            out.line(res)


class db_set:
    """Set a low level setting."""

    def add_arguments(self, parser):
        parser.add_argument("key", type=slash_scoped_key, help="low level database key")
        parser.add_argument("value", type=str, help="low level key value")

    def run(self, bot, args, out):
        scope, key = args.key
        bot.set(key, args.value, scope=scope)


class db_list:
    """List all key,values. """

    def add_arguments(self, parser):
        parser.add_argument(
            "--scope", type=str,
            help="slash-terminated scope of db key", default=None)

    def run(self, bot, args, out):
        res = bot.list_settings(args.scope)
        for key, res in res:
            out.line("{}: {}".format(key, res))


def command_set(command, replies):
    """show all/one per-peer settings or set a value for a setting.

    Examples:

    # show all settings
    /set

    # show value for one setting
    /set name

    # set one setting
    /set name=value
    """
    addr = command.message.get_sender_contact().addr
    if not command.payload:
        text = "\n".join(dump_settings(command.bot, scope=addr))
    elif "=" in command.payload:
        name, value = command.payload.split("=", 1)
        name = name.strip()
        value = value.strip()
        old = command.bot.set(name, value, scope=addr)
        text = "old: {}={}\nnew: {}={}".format(name, repr(old), name, repr(value))
    else:
        x = command.bot.get(command.args[0], scope=addr)
        text = "{}={}".format(command.args[0], x)
    replies.add(text=text)


def dump_settings(bot, scope):
    lines = []
    for name, value in bot.list_settings(scope=scope):
        lines.append("{}={}".format(name, value))
    if not lines:
        lines.append("no settings")
    return lines


class TestCommandSettings:
    def test_mock_get_set_empty_settings(self, mocker):
        reply_msg = mocker.run_command("/set")
        assert reply_msg.text.startswith("no settings")

    def test_mock_set_works(self, mocker):
        reply_msg = mocker.run_command("/set hello=world")
        assert "old" in reply_msg.text
        msg_reply = mocker.run_command("/set")
        assert "hello=world" == msg_reply.text

    def test_get_set_functional(self, bot_tester):
        msg_reply = bot_tester.send_command("/set hello=world")
        msg_reply = bot_tester.send_command("/set hello2=world2")
        msg_reply = bot_tester.send_command("/set hello")
        assert msg_reply.text == "hello=world"
        msg_reply = bot_tester.send_command("/set")
        assert "hello=world" in msg_reply.text
        assert "hello2=world2" in msg_reply.text
