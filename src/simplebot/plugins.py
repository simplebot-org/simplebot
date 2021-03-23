import pluggy

from .hookspec import DeltaBotSpecs, spec_name


class Plugins:
    def __init__(self, logger, plugin_manager) -> None:
        assert plugin_manager
        self._pm = plugin_manager
        self.logger = logger
        self.hook = self._pm.hook

    def add_module(self, name, module) -> None:
        """ add a named simplebot plugin python module. """
        self.logger.debug("registering plugin {!r}".format(name))
        self._pm.register(plugin=module, name=name)
        self._pm.check_pending()

    def remove(self, name) -> None:
        """ remove a named simplebot plugin. """
        self.logger.debug("removing plugin {!r}".format(name))
        self._pm.unregister(name=name)

    def dict(self) -> dict:
        """ return a dict name->simplebot plugin object mapping. """
        return dict(self._pm.list_name_plugin())

    def items(self) -> list:
        """ return (name, plugin obj) list. """
        return self._pm.list_name_plugin()


_pm = None


def get_global_plugin_manager():
    global _pm
    if _pm is None:
        _pm = make_plugin_manager()
    return _pm


def make_plugin_manager():
    from .builtin import admin, cmdline, db, log, settings

    pm = pluggy.PluginManager(spec_name)
    pm.add_hookspecs(DeltaBotSpecs)

    # register builtin modules
    pm.register(plugin=admin, name=".builtin.admin")
    pm.register(plugin=settings, name=".builtin.settings")
    pm.register(plugin=db, name=".builtin.db")
    pm.register(plugin=cmdline, name=".builtin.cmdline")
    pm.register(plugin=log, name=".builtin.log")
    pm.check_pending()
    # register setuptools modules
    pm.load_setuptools_entrypoints("simplebot.plugins")
    return pm
