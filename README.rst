SimpleBot
=========

An extensible Delta Chat bot. 

Install
-------

To install SimpleBot run the following command (preferably in a ``virtualenv``):

.. code-block:: bash

   $ pip3 install simplebot

Try typing "simplebot --version" to verify it worked.

.. note::

    SimpleBot requires Delta Chat's Python bindings.  On Linux bindings
    have pre-built binary wheels and thus the above deltabot install should just work.
    On other platforms you need to install the bindings from source, see
    `deltachat Python bindings readme <https://github.com/deltachat/deltachat-core-rust/tree/master/python>`_.


Initialize the bot
------------------

Configure an e-mail address for your chat bot (using example credentials)::

    simplebot init tmp.vd9dd@testrun.org OzrSxdx5hiaD


Running the bot
---------------

If initialization ended successfully, now you can run the bot::

    simplebot serve

Within a Delta Chat app, you may now send a chat `/help` message to
`tmp.vd9dd@testrun.org` and should get a short list of available commands
in the reply.


Plugins
-------

SimpleBot is a bit useless without plugins, so once you have your bot working you probably want to install some plugins, for official plugins see:

https://github.com/SimpleBot-Inc/simplebot_plugins

Installing script plugins
-------------------------

If you know how to code in Python, you can quickly create plugins and install them to tweak your bot::

    $ simplebot add-module ~/my_plugins/server_stats.py

See the `examples` folder to see some examples about how to create plugins this way.


Note for users
--------------

SimpleBot uses `Autocrypt <https://autocrypt.org/>`_ end-to-end encryption
but note that the operator of the bot service can look into
messages that are sent to it.
