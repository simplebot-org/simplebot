"""
This example illustrates how to add commands and filters dynamically.
"""

import os

import simplebot


@simplebot.hookimpl
def deltabot_init(bot):
    if os.environ.get("LANG", "").startswith("es_"):  # Spanish locale
        name = "/mi_eco"
        description = "Repite el texto enviado"
    else:
        name = "/my_echo"
        description = "Echoes back the given text"
    admin_only = os.environ.get("BOT_ADMIN_ONLY") == "1"
    bot.commands.register(
        func=echo_command,
        name=name,
        help=description,
        admin=admin_only,
    )

    if os.environ.get("BOT_ENABLE_FILTER"):
        bot.filters.register(func=echo_filter, help=description, admin=admin_only)


def echo_command(payload, replies):
    replies.add(text=payload)


def echo_filter(message, replies):
    replies.add(text=message.text)


class TestSendFile:
    def test_cmd(self, mocker):
        msgs = mocker.get_replies("/my_echo hello")
        if len(msgs) == 1:
            msg = msgs[0]
        else:
            msg = mocker.get_one_reply("/mi_eco hello")
        assert msg.text == "hello"

    def test_filter(self, mocker):
        if not os.environ.get("BOT_ENABLE_FILTER"):
            mocker.bot.filters.register(func=echo_filter, help="test")

        msg = mocker.get_one_reply("hello", filters=__name__)
        assert msg.text == "hello"
