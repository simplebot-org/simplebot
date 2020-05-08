
import pytest

from deltabot.commands import parse_command_docstring


def test_parse_command_docstring():
    with pytest.raises(ValueError):
        parse_command_docstring(lambda: None)

    def func(command):
        """short description.

        long description.
        """
    short, long = parse_command_docstring(func)
    assert short == "short description."
    assert long == "long description."


def test_run_help(mocker):
    reply = mocker.run_command("/help")
    assert "/help" in reply.text


def test_register(mock_bot):
    def my_command(command):
        """ my commands example. """

    mock_bot.commands.register(name="/example", func=my_command)
    assert "/example" in mock_bot.commands.dict()
    with pytest.raises(ValueError):
        mock_bot.commands.register(name="/example", func=my_command)

    mock_bot.commands.unregister("/example")
    assert "/example" not in mock_bot.commands.dict()
