"""
This example illustrates how to register functions as commands/filters.
"""

import simplebot

version = "0.1.0"


@simplebot.command
def echo(payload, replies):
    """Echoes back text. Example: /echo hello world"""
    replies.add(text=payload or "echo")


@simplebot.filter
def echo_filter(message, replies):
    """Echoes back received message."""
    replies.add(text=message.text)


class TestEcho:
    def test_echo(self, mocker):
        msg = mocker.get_one_reply("/echo")
        assert msg.text == "echo"

        msg = mocker.get_one_reply("/echo hello world")
        assert msg.text == "hello world"

    def test_echo_filter(self, mocker):
        text = "testing echo filter"
        msg = mocker.get_one_reply(text, filters=__name__)
        assert msg.text == text

        text = "testing echo filter in group"
        msg = mocker.get_one_reply(text, group="mockgroup", filters=__name__)
        assert msg.text == text
