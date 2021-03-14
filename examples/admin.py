"""
This example illustrates how to add administrator commands, normal users
will not see or be able to use this commands, only bot administrators can.
To add a bot administrator you have to run in the command line:

    $ simplebot admin --add me@example.com
"""

import simplebot


@simplebot.command(admin=True)
def kick(message):
    """Kick from group the user that sent the quoted message.

    You must use the command in a group, swipe to reply a message and send:
    /kick
    as reply to the message, the bot will remove the sender of that message
    from the group. This can be useful in big groups.
    """
    message.chat.remove_contact(message.quote.get_sender_contact())


@simplebot.command(admin=True)
def status(bot, payload, replies):
    """Set bot status message.

    Example: /status I am way too cool.
    """
    bot.account.set_config('selfstatus', payload)
    replies.add(text='Status updated.')
