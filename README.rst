Deltabot Quickstart: implement and run a chat bot with Python
=============================================================

Deltabot allows to implement and run chat bots for `Delta Chat`_.

Install
-------

To install deltabot run the following command (preferably in a ``virtualenv``):

.. code-block:: bash

   $ pip3 install deltabot

Try typing "deltabot --version" to verify it worked.

.. note::

    Deltabot requires Delta Chat's Python bindings.  On Linux bindings
    have pre-built binary wheels and thus the above deltabot install should just work.
    On other platforms you need to install the bindings from source, see
    `deltachat Python bindings readme <https://github.com/deltachat/deltachat-core-rust/tree/master/python>`_.


Initialize the bot
-----------------------

Configure an e-mail address for your chat bot (using example credentials)::

    deltabot init tmp.vd9dd@testrun.org OzrSxdx5hiaD

Within a Delta Chat app (or another e-mail client), you may now
send a chat `/help` message to `tmp.vd9dd@testrun.org` and should
get a short list of available commands in the reply.


Try out an example "calculator" bot
----------------------------------------------

Checkout the deltabot repo to play with some example bots::

    git clone https://github.com/deltachat/deltabot
    cd deltabot

Now you can register an example bot and send/receive messages:

1. Register the example "mycalc bot"::

    $ deltabot add-module example/mycalc.py

2. Now start serving the chat bot::

    $ deltabot serve

3. Within an Delta Chat app, you may now send a chat `/help` message
   to `tmp.vd9dd@testrun.org` and should get a short list
   of available commands in the reply. Send `/mycalc 23+20-1` and
   wait for the the answer.

Note that the bot-answer speed largely depends on the provider you are
using for the bot-email address.  On test servers we get 3-5 seconds
full roundtrips, between question and answer arriving back.


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

For many more examples and Deltabot plugins see:

https://github.com/SimpleBot-Inc/simplebot_plugins


.. _Delta Chat: https://delta.chat
