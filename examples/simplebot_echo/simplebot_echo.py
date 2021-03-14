"""
This example illustrates how to register functions as commands/filters.
"""

import simplebot

version = '0.1.0'


@simplebot.command
def echo(payload, replies):
    """Echoes back text. Example: /echo hello world"""
    replies.add(text=payload or 'echo')


@simplebot.filter(name='echo_filter')
def process_messages(message, replies):
    """ Echoes back received message."""
    replies.add(text=message.text)
