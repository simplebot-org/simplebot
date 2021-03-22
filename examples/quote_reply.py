"""
This example illustrates how to quote-reply a message.
"""

import re

import simplebot


@simplebot.command
def mycalc(payload, message, replies):
    """caculcates result of arithmetic integer expression.

    send "/mycalc 23+20" to the bot to get the result "43" back
    """
    # don't directly use eval() as it could execute arbitrary code
    parts = re.split(r"[\+\-\*\/]", payload)
    try:
        for part in parts:
            int(part.strip())
    except ValueError:
        reply = "ExpressionError: {!r} not an int in {!r}".format(part, payload)
    else:
        # now it's safe to use eval
        reply = "result of {!r}: {}".format(payload, eval(payload))

    replies.add(text=reply, quote=message)


class TestQuoteReply:
    def test_mock_calc(self, mocker):
        reply_msg = mocker.get_one_reply("/mycalc 1+1")
        assert reply_msg.text.endswith("2")

    def test_mock_calc_fail(self, mocker):
        reply_msg = mocker.get_one_reply("/mycalc 1w+1")
        assert "ExpressionError" in reply_msg.text

    def test_bot_mycalc(self, bot_tester):
        msg_reply = bot_tester.get_one_reply("/mycalc 10*13+2")
        assert msg_reply.text.endswith("132")
