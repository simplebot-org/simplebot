from queue import Queue

import pluggy

import simplebot
from simplebot.plugins import get_global_plugin_manager


def test_globality_plugin_manager(monkeypatch):
    monkeypatch.setattr(simplebot.plugins, "_pm", None)
    pm1 = get_global_plugin_manager()
    pm2 = get_global_plugin_manager()
    assert pm1 == pm2
    monkeypatch.undo()
    assert pm1 != get_global_plugin_manager()


def test_builtin_plugins(mock_bot):
    assert ".builtin.db" in mock_bot.plugins.dict()
    mock_bot.plugins.remove(name=".builtin.db")
    assert ".builtin.db" not in mock_bot.plugins.dict()


def test_setuptools_plugin(monkeypatch, request):
    l = []

    def load_setuptools_entrypoints(self, group, name=None):
        l.append((group, name))

    monkeypatch.setattr(
        pluggy.PluginManager,
        "load_setuptools_entrypoints",
        load_setuptools_entrypoints,
    )
    _ = request.getfixturevalue("mock_bot")
    assert l == [("simplebot.plugins", None)]


def test_deltabot_init_hooks(monkeypatch, request):
    q = Queue()

    class MyPlugin:
        @simplebot.hookimpl
        def deltabot_init(self, bot):
            # make sure db is ready and initialized
            bot.set("hello", "world")
            assert bot.get("hello") == "world"
            q.put(1)

        @simplebot.hookimpl
        def deltabot_start(self, bot):
            q.put(2)

    def load_setuptools_entrypoints(self, group, name=None):
        self.register(MyPlugin())

    monkeypatch.setattr(
        pluggy.PluginManager,
        "load_setuptools_entrypoints",
        load_setuptools_entrypoints,
    )
    bot = request.getfixturevalue("mock_stopped_bot")
    assert q.get(timeout=10) == 1
    bot.start()
    assert q.get(timeout=10) == 2
