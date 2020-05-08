
import re

from deltabot import deltabot_hookimpl


@deltabot_hookimpl
def deltabot_init(bot):
    bot.commands.register(
        name="/mycalc",
        func=process_command_mycalc
    )


def process_command_mycalc(command):
    """caculcates result of arithmetic integer expression.

    send "/mycalc 23+20" to the bot to get the result "43" back
    """
    text = command.payload

    # don't directly use eval() as it could execute arbitrary code
    parts = re.split(r"[\+\-\*\/]", text)
    try:
        for part in parts:
            int(part.strip())
    except ValueError:
        reply = "ExpressionError: {!r} not an int in {!r}".format(part, text)
    else:
        # now it's safe to use eval
        reply = "result of {!r}: {}".format(text, eval(text))

    return reply


class TestMyCalc:
    def test_mock_calc(self, mocker):
        reply_msg = mocker.run_command("/mycalc 1+1")
        assert reply_msg.text.endswith("2")

    def test_mock_calc_fail(self, mocker):
        reply_msg = mocker.run_command("/mycalc 1w+1")
        assert "ExpressionError" in reply_msg.text

    def test_bot_mycalc(self, bot_tester):
        msg_reply = bot_tester.send_command("/mycalc 10*13+2")
        assert msg_reply.text.endswith("132")
