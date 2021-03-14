SimpleBot
=========

An extensible Delta Chat bot. 

Install
-------

To install simplebot run the following commands (preferably in a ``virtualenv``)::

  $ pip3 install -U pip wheel
  $ pip3 install --pre -U -i https://m.devpi.net/dc/master deltachat
  $ pip3 install https://github.com/simplebot-org/simplebot/archive/master.zip

**NOTE:** If Delta Chat Python bindings package is not available for your platform you will need to compile and install the bindings manually, check deltachat package documentation for more info.


Quick Start: Running a bot+plugins
----------------------------------

(Replace variables ``$ADDR`` and ``$PASSWORD`` with the email and password for the account the bot will use)

1. Add an account to the bot::

     $ simplebot init "$ADDR" "$PASSWORD"

2. Install some official plugins::

     $ git clone https://github.com/simplebot-org/simplebot_plugins
     $ python3 simplebot_plugins/scripts/install_plugin.py

3. Start the bot::

     $ simplebot --account $ADDR serve


Plugins
-------

SimpleBot is a base bot that relies on plugins to add functionality, for official plugins see:

https://github.com/simplebot-org/simplebot_plugins

Plugins installed as Python packages (for example with ``pip``) are global to all accounts you register in the bot, to separate plugins per account you need to run each account in its own virtual environment.


Creating per account plugins
----------------------------

If you know how to code in Python, you can quickly create plugins and install them to tweak your bot.

Lets create an "echo bot", create a file named ``echo.py`` and write inside:

.. code:: python

    import simplebot

    @simplebot.filter
    def echo(message, replies):
    """ Echoes back received message."""
        replies.add(text=message.text)

That is it! you have created a plugin that will transform simplebot in an "echo bot" that will echo back any text message you send to it. Now tell simplebot to register your plugin::

    $ simplebot --account $ADDR plugin --add ./echo.py

Now you can run the bot with ``simplebot --account $ADDR serve`` and write to it from Delta Chat app to check it works.

Check the ``examples`` folder to see some examples about how to create plugins.


Note for users
--------------

SimpleBot uses `Autocrypt <https://autocrypt.org/>`_ end-to-end encryption
but note that the operator of the bot service can look into
messages that are sent to it.


Credits
-------

SimpleBot is based on `deltabot <https://github.com/deltachat-bot/deltabot>`_

SimpleBot logo was created by Cuban designer "Dann".
