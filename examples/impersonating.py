"""
This example illustrates how to send a message impersonating another user
in groups.
This plugin uses a 3rd party lib so you will need to install it first:

    $ pip install wikiquote

"""

import simplebot
import wikiquote


@simplebot.command
def quote(message, replies):
    """Get quote of the day from Wikiquote."""
    text, author = wikiquote.quote_of_the_day()
    if message.chat.is_group():
        replies.add(text=text, sender=author)
    else:
        replies.add(text='"{}"\n\n― {}'.format(text, author))

