<p align="center"><img height="180" width="180" src="https://github.com/simplebot-org/simplebot/raw/master/artwork/Bot.svg"></p>
<h1 align="center">SimpleBot</h1>

[![Latest Release](https://img.shields.io/pypi/v/simplebot.svg)](https://pypi.org/project/simplebot)
[![Supported Versions](https://img.shields.io/pypi/pyversions/simplebot.svg)](https://pypi.org/project/simplebot)
[![Downloads](https://pepy.tech/badge/simplebot)](https://pepy.tech/project/simplebot)
[![License](https://img.shields.io/pypi/l/simplebot.svg)](https://pypi.org/project/simplebot)
[![CI](https://github.com/simplebot-org/simplebot/actions/workflows/python-ci.yml/badge.svg)](https://github.com/simplebot-org/simplebot/actions/workflows/python-ci.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Contributors](https://img.shields.io/github/contributors/simplebot-org/simplebot.svg)](https://github.com/simplebot-org/simplebot/graphs/contributors)

> An extensible Delta Chat bot.

## Install

To install the latest stable version of SimpleBot run the following command (preferably in a [virtual environment](https://packaging.python.org/tutorials/installing-packages/#creating-and-using-virtual-environments)):

```sh
pip install simplebot
```

To test unreleased version:

```sh
pip install --pre -U -i https://m.devpi.net/dc/master deltachat
pip install git+https://github.com/simplebot-org/simplebot
```

> **⚠️ NOTE:** If Delta Chat Python bindings package is not available for your platform you will need to compile and install the bindings manually, check [deltachat documentation](https://github.com/deltachat/deltachat-core-rust/blob/master/python/README.rst) for more info.


## Quick Start: Running a bot+plugins

(Replace variables `$ADDR` and `$PASSWORD` with the email and password for the account the bot will use)

1. Add an account to the bot:

	```sh
	simplebot init "$ADDR" "$PASSWORD"
	```

2. Install some plugins:

	```sh
	pip install simplebot-echo
	```

3. Start the bot:

	```sh
	simplebot serve
	```

## Plugins

SimpleBot is a base bot that relies on plugins to add functionality.

Everyone can publish their own plugins, search in PyPI to discover cool [SimpleBot plugins](https://pypi.org/search/?q=simplebot&o=&c=Environment+%3A%3A+Plugins)

> **⚠️ NOTE:** Plugins installed as Python packages (for example with `pip`) are global to all accounts you register in the bot, to separate plugins per account you need to run each account in its own virtual environment.

## Creating per account plugins

If you know how to code in Python, you can quickly create plugins and install them to tweak your bot.

Lets create an "echo bot", create a file named `echo.py` and write inside:

```python
import simplebot

@simplebot.filter
def echo(message, replies):
    """Echoes back received message."""
    replies.add(text=message.text)
```

That is it! you have created a plugin that will transform simplebot in an "echo bot" that will echo back any text message you send to it. Now tell simplebot to register your plugin:

```sh
simplebot plugin --add ./echo.py
```

Now you can start the bot and write to it from Delta Chat app to see your new bot in action.

Check the `examples` folder to see some examples about how to create plugins.

## Note for users

SimpleBot uses [Autocrypt](https://autocrypt.org/) end-to-end encryption
but note that the operator of the bot service can look into
messages that are sent to it.


## Credits

SimpleBot is based on [deltabot](https://github.com/deltachat-bot/deltabot)

SimpleBot logo was created by Cuban designer "Dann".
