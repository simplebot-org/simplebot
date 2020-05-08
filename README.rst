Deltabot Quickstart: implement and run a chat bot with Python
=============================================================

Deltabot allows to implement and run chat bots for `Delta Chat`_.

Install
-------

To install it run the following command (preferably in a ``virtualenv``):

.. code-block:: bash

   $ pip3 install deltabot


Init and run a bare bot
-----------------------

Configure an e-mail address for your chat bot (using example credentials)::

    deltabot init tmp.vd9dd@testrun.org OzrSxdx5hiaD

Now start the bot::

    deltabot serve

Within an Delta Chat app, you may now send a chat `/help` message to
`tmp.vd9dd@testrun.org` and should get a short list of available
commands in the reply.


Try out an example "calculator" bot (TOBEDONE)
----------------------------------------------

Here is a complete "calculator" chat bot for performing additions::

    # contents of example/mycalc.py


Test the "mycalc bot"::

    $ deltabot test example/mycalc.py

Register the new "mycalc bot"::

    $ deltabot add-module example/mycalc.py

Now start serving the chat bot::

    $ deltabot serve

and text a `/mycalc 23+20-1` message, and see the result message arriving back.

Writing setuptools plugins
--------------------------

You can implement your plugin as a proper python package or wheel
by using setuptools.  Have a look in the `examples/deltachat_echo`
example directory which contains a complete example.


note for users
--------------

Deltabot uses `Autocrypt <https://autocrypt.org/>`_ end-to-end encryption
but note that the operator of the bot service can look into
messages that are sent to it.


Plugins
-------

See: https://github.com/SimpleBot-Inc/simplebot_plugins


.. _Delta Chat: https://delta.chat
