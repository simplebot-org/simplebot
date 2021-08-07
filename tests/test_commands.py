import pytest

from simplebot.bot import Replies
from simplebot.commands import parse_command_docstring


def test_parse_command_docstring():
    with pytest.raises(ValueError):
        parse_command_docstring(lambda: None, args=[])

    def func(replies, command):
        """short description.

        long description.
        """

    short, long, args = parse_command_docstring(func, args="command replies".split())
    assert short == "short description."
    assert long == "long description."
    assert len(args) == 2


def test_run_help(mocker):
    reply = mocker.get_one_reply("/help")
    assert "/help" in reply.html


def test_partial_args(mock_bot):
    def my_command(replies):
        """this command only needs the "replies" argument"""

    mock_bot.commands.register(name="/example", func=my_command)


def test_fail_args(mock_bot):
    def my_command(unknown_arg):
        """invalid"""

    with pytest.raises(ValueError):
        mock_bot.commands.register(name="/example", func=my_command)


def test_register(mock_bot):
    def my_command(command, replies):
        """my commands example."""

    mock_bot.commands.register(name="/example", func=my_command)
    assert "/example" in mock_bot.commands.dict()
    with pytest.raises(ValueError):
        mock_bot.commands.register(name="/example", func=my_command)

    mock_bot.commands.unregister("/example")
    assert "/example" not in mock_bot.commands.dict()


class TestArgParsing:
    @pytest.fixture
    def parse_cmd(self, mocker):
        def proc(name, text, group=None):
            l = []

            def my_command(command, replies):
                """my commands example."""
                l.append(command)

            mocker.bot.commands.register(name=name, func=my_command)
            mocker.replies = mocker.get_replies(text, group=group)
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
        parse_cmd("/some_group", "/unknown", group="mockgroup")
        assert not mocker.replies
        parse_cmd("/some_other", "/unknown", group=None)
        assert mocker.replies

    def test_two_commands_with_same_prefix(self, parse_cmd):
        assert parse_cmd("/execute", "/execute").cmd_def.cmd == "/execute"
        assert parse_cmd("/exec", "/exec").cmd_def.cmd == "/exec"
