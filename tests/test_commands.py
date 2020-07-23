
import pytest

from deltabot.commands import parse_command_docstring
from deltabot.bot import Replies


def test_parse_command_docstring():
    with pytest.raises(ValueError):
        parse_command_docstring(lambda: None, args=[])

    def func(command, replies):
        """short description.

        long description.
        """
    short, long = parse_command_docstring(func, args="command replies".split())
    assert short == "short description."
    assert long == "long description."


def test_run_help(mocker):
    reply = mocker.run_command("/help")
    assert "/help" in reply.text


def test_fail_args(mock_bot):
    def my_command(command):
        """ invalid """

    with pytest.raises(ValueError):
        mock_bot.commands.register(name="/example", func=my_command)


def test_register(mock_bot):
    def my_command(command, replies):
        """ my commands example. """

    mock_bot.commands.register(name="/example", func=my_command)
    assert "/example" in mock_bot.commands.dict()
    with pytest.raises(ValueError):
        mock_bot.commands.register(name="/example", func=my_command)

    mock_bot.commands.unregister("/example")
    assert "/example" not in mock_bot.commands.dict()


class TestArgParsing:

    @pytest.fixture
    def parse_cmd(self, mock_bot, mocker):
        def proc(name, text, group=False):
            l = []

            def my_command(command, replies):
                """ my commands example. """
                l.append(command)

            mock_bot.commands.register(name=name, func=my_command)

            msg = mocker.make_incoming_message(text, group=group)
            replies = Replies(msg, mock_bot.logger)
            mocker.replies = replies
            mock_bot.commands.deltabot_incoming_message(message=msg, replies=replies)
            if len(l) == 1:
                return l[0]

        return proc

    def test_basic(self, parse_cmd):
        command = parse_cmd("/some", "/some 123")
        assert command.args == ["123"]
        assert command.payload == "123"

    def test_under1(self, parse_cmd):
        command = parse_cmd("/some", "/some_123 456")
        assert command.args == ["123", "456"]
        assert command.payload == "123 456"

    def test_under2(self, parse_cmd):
        command = parse_cmd("/some", "/some_123_456")
        assert command.args == ["123", "456"]
        assert command.payload == "123 456"

    def test_multiline_payload(self, parse_cmd):
        command = parse_cmd("/some", "/some_123 456\n789_yes")
        assert command.args == ["123", "456", "789_yes"]
        assert command.payload == "123 456\n789_yes"

    def test_under_with_under_command(self, parse_cmd):
        command = parse_cmd("/some_group", "/some_group_123_456")
        assert command.args == ["123", "456"]
        assert command.payload == "123 456"

    def test_under_conflict(self, parse_cmd):
        parse_cmd("/some", "/some")
        with pytest.raises(ValueError):
            parse_cmd("/some_group_long", "")
        with pytest.raises(ValueError):
            parse_cmd("/some_group", "")

    def test_under_conflict2(self, parse_cmd):
        parse_cmd("/some_group", "/some_group")
        with pytest.raises(ValueError):
            parse_cmd("/some", "")

    def test_two_commands_with_different_subparts(self, parse_cmd):
        assert parse_cmd("/some_group", "/some_group").cmd_def.cmd == "/some_group"
        assert parse_cmd("/some_other", "/some_other").cmd_def.cmd == "/some_other"

    def test_unknown_command(self, parse_cmd, mocker):
        parse_cmd("/some_group", "/unknown", group=True)
        assert not mocker.replies.has_replies()
        parse_cmd("/some_other", "/unknown", group=False)
        assert mocker.replies.has_replies()
