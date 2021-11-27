"""
This example illustrates how to control filter execution order.
"""

import simplebot

blacklist = ["user1@example.com", "user2@example.org"]


@simplebot.filter(tryfirst=True)
def validate(message):
    """Check that the sender is not in the blacklist."""
    if message.get_sender_contact().addr in blacklist:
        # this will prevent other filters to process the message
        # NOTE: this doesn't apply to commands!
        return True


@simplebot.filter
def reply_salute(message, replies):
    """Reply to some common salutes."""
    if message.text in ("hi", "hello", "howdy"):
        replies.add(text=message.text, quote=message)


@simplebot.filter(trylast=True)
def send_help(replies):
    """Send some hints to the sender if the message was not replied by a previous filter."""
    if not replies.has_replies():
        replies.add(text='I don\'t understand, send "hi"')


class TestFilterPriority:
    def test_validate(self, mocker):
        import pytest

        mocker.get_one_reply(text="test validate", filters=__name__)

        msgs = mocker.get_replies(
            text="test validate", addr=blacklist[1], filters=__name__
        )
        assert not msgs

    def test_reply_salute(self, mocker):
        text = "hello"
        msg = mocker.get_one_reply(text=text, filters=__name__)
        assert msg.text == text

    def test_send_help(self, mocker):
        resp = "I don't understand"

        msg = mocker.get_one_reply(text="test send_help", filters=__name__)
        assert resp in msg.text

        msg = mocker.get_one_reply(text="hello", filters=__name__)
        assert resp not in msg.text
