# -*- coding: utf-8 -*-
from deltabot.hookspec import deltabot_hookimpl


version = '0.5'


@deltabot_hookimpl
def deltabot_init(bot):
    bot.commands.register(name="/echo", func=process_command_echo)


def process_command_echo(command, replies):
    """ Echoes back received message.

    To use it you can simply send a message starting with
    the command '/echo'. Example: `/echo hello world`
    """
    message = command.message
    contact = message.get_sender_contact()
    sender = 'From: {} <{}>'.format(contact.display_name, contact.addr)
    replies.add(text="{}\n{!r}".format(sender, command.payload))


def test_mock_echo(mocker):
    reply = mocker.run_command("/echo")
    assert reply.text.startswith("From")

    reply = mocker.run_command("/echo hello")
    assert reply.text.startswith("From")
    assert reply.text.endswith("'hello'")


def test_mock_echo_help(mocker):
    reply = mocker.run_command("/help").text.lower()
    assert "/echo" in reply
    assert "/help" in reply
    assert "plugins: " in reply


def test_echo(bot_tester):
    msg_reply = bot_tester.send_command("/echo")
    assert msg_reply.text.startswith("From")
    assert bot_tester.own_addr in msg_reply.text
    assert bot_tester.own_displayname in msg_reply.text
