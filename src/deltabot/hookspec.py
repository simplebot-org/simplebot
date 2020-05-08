
import pluggy

spec_name = "deltabot"
deltabot_hookspec = pluggy.HookspecMarker(spec_name)
deltabot_hookimpl = pluggy.HookimplMarker(spec_name)


class DeltaBotSpecs:
    """ per DeltaBot instance hook specifications. """

    @deltabot_hookspec
    def deltabot_init_parser(self, parser):
        """ initialize the deltabot main parser with new options and subcommands.

        :param parser: a :class:`deltabot.parser.MyArgumentParser` instance where you can
                        call `add_subcommand(name, func)` to get a sub parser where you
                        can then add arguments.
        """

    @deltabot_hookspec(firstresult=True)
    def deltabot_get_logger(self, args):
        """ get a logger based on the parsed command line args.

        The returned logger needs to offer info/debug/warn/error methods.
        """

    @deltabot_hookspec(historic=True)
    def deltabot_init(self, bot, args):
        """ init a bot -- called before the bot starts serving requests.

        Note that plugins that register after DeltaBot initizialition
        will see their hookimpl get called during plugin registration.
        This allows "late" plugins to still register commands and filters.
        """

    @deltabot_hookspec
    def deltabot_shutdown(self, bot):
        """ shutdown all resources of the bot. """

    @deltabot_hookspec(firstresult=True)
    def deltabot_incoming_message(self, message, bot, replies):
        """ process an incoming fresh message.

        :param replies: call replies.add() to schedule a reply.
        """

    @deltabot_hookspec(firstresult=True)
    def deltabot_store_setting(self, key, value):
        """ store a named bot setting persistently. """

    @deltabot_hookspec(firstresult=True)
    def deltabot_get_setting(self, key):
        """ get a named persistent bot setting."""

    @deltabot_hookspec(firstresult=True)
    def deltabot_list_settings(self):
        """ get a list of persistent (key, value) tuples. """
