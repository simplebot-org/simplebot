
import pluggy
import deltabot
from deltabot.plugins import get_global_plugin_manager


def test_globality_plugin_manager(monkeypatch):
    monkeypatch.setattr(deltabot.plugins, "_pm", None)
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
        pluggy.manager.PluginManager,
        "load_setuptools_entrypoints",
        load_setuptools_entrypoints
    )
    _ = request.getfixturevalue("mock_bot")
    assert l == [("deltabot.plugins", None)]
