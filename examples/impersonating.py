"""
This example illustrates:

* how to send a message impersonating another user.
* how to define preferences that can be customized by each user.

This plugin uses a 3rd party lib so you will need to install it first:

    $ pip install wikiquote

"""

import wikiquote

import simplebot


@simplebot.hookimpl
def deltabot_init(bot):
    bot.add_preference("locale", "Bot language, example values: en, es, de")


@simplebot.command
def quote(bot, message, replies):
    """Get quote of the day from Wikiquote."""
    lang = bot.get("locale", scope=message.get_sender_contact().addr)
    if lang:
        text, author = wikiquote.quote_of_the_day(lang=lang)
    else:
        text, author = wikiquote.quote_of_the_day()
    replies.add(text=text, sender=author)


class TestImpersonating:
    def test_impersonating(self, mocker):
        msg = mocker.get_one_reply(text="/quote")
        assert msg.override_sender_name
