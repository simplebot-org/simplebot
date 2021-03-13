
import os

from ..commands import command_decorator
from ..hookspec import deltabot_hookimpl
from ..utils import get_builtin_avatar, get_builtin_avatars


@deltabot_hookimpl
def deltabot_init_parser(parser) -> None:
    parser.add_subcommand(db_cmd)
    parser.add_subcommand(avatar)
    parser.add_subcommand(set_name)
    parser.add_subcommand(set_config)


def slash_scoped_key(key: str) -> tuple:
    i = key.find("/")
    if i == -1:
        raise ValueError("key {!r} does not contain a '/' scope delimiter")
    return (key[:i], key[i + 1:])


class avatar:
    """set bot avatar, or show available builtin avatars if no path is given."""
    def add_arguments(self, parser) -> None:
        parser.add_argument('avatar', metavar='PATH', nargs='?',
                            help='path to the avatar image.')

    def run(self, bot, args, out) -> None:
        if not args.avatar:
            out.line('Builtin avatars:')
            for name in get_builtin_avatars():
                out.line(name)
        else:
            path = get_builtin_avatar(args.avatar)
            if os.path.exists(path):
                args.avatar = path
            bot.account.set_avatar(args.avatar)
            out.line('Avatar updated.')


class set_name:
    """set bot display name."""
    def add_arguments(self, parser) -> None:
        parser.add_argument('name', type=str, help='the new display name')

    def run(self, bot, args, out) -> None:
        bot.account.set_config('displayname', args.name)


class set_config:
    """set low level delta chat configuration."""
    def add_arguments(self, parser) -> None:
        parser.add_argument('key', type=str, help='configuration key')
        parser.add_argument('value', type=str, help='configuration new value')

    def run(self, bot, args, out) -> None:
        bot.account.set_config(args.key, args.value)


class db_cmd:
    """low level settings."""
    name = 'db'

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '-l', '--list', help="list all key,values.", metavar='SCOPE',
            nargs='?')
        parser.add_argument(
            '-g', '--get', help="get a low level setting.", metavar="KEY",
            type=slash_scoped_key)
        parser.add_argument(
            '-s', '--set', help="set a low level setting.",
            metavar=('KEY', 'VALUE'), nargs=2)
        parser.add_argument(
            '-d', '--del', help="delete a low level setting.", metavar="KEY",
            type=slash_scoped_key, dest='_del')

    def run(self, bot, args, out) -> None:
        if args.get:
            self._get(bot, *args.get, out)
        elif args._del:
            self._del(bot, *args._del, out)
        elif args.set:
            self._set(bot, *args.set)
        else:
            self._list(bot, args.list, out)

    def _get(self, bot, scope, key, out) -> None:
        res = bot.get(key, scope=scope)
        if res is None:
            out.fail("key {}/{} does not exist".format(scope, key))
        else:
            out.line(res)

    def _set(self, bot, key, value) -> None:
        scope, key = slash_scoped_key(key)
        bot.set(key, value, scope=scope)

    def _list(self, bot, scope, out) -> None:
        for key, res in bot.list_settings(scope):
            if "\n" in res:
                out.line("{}:".format(key))
                for line in res.split("\n"):
                    out.line("   " + line)
            else:
                out.line("{}: {}".format(key, res))

    def _del(self, bot, scope, key, out) -> None:
        res = bot.get(key, scope=scope)
        if res is None:
            out.fail("key {}/{} does not exist".format(scope, key))
        else:
            bot.delete(key, scope=scope)
            out.line("key '{}/{}' deleted".format(scope, key))


@command_decorator(name='/set')
def cmd_set(command, replies) -> None:
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


def dump_settings(bot, scope) -> list:
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
