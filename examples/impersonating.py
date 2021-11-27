"""
This example illustrates:

* how to send a message impersonating another username.
* how to define preferences that can be customized by each user.
"""

import simplebot


@simplebot.hookimpl
def deltabot_init(bot):
    bot.add_preference("name", "the name to impersonate")


@simplebot.filter
def filter_messages(bot, message, replies):
    """Send me any message in private and I will reply with the same message but impersonating another username."""
    if not message.chat.is_group() and message.text:
        sender = message.get_sender_contact()
        name = bot.get("name", scope=sender.addr) or sender.name
        replies.add(text=message.text, sender=name)


class TestImpersonating:
    def test_impersonating(self, mocker):
        msg = mocker.get_one_reply(text="hello", filters=__name__)
        assert msg.override_sender_name
