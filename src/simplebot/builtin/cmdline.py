
import os

from ..hookspec import deltabot_hookimpl


@deltabot_hookimpl
def deltabot_init_parser(parser):
    from .. import __version__ as simplebot_version

    parser.add_subcommand(Init)
    parser.add_subcommand(Info)
    parser.add_subcommand(Serve)
    parser.add_subcommand(PluginCmd)

    parser.add_generic_option(
        "--version", action="version", version=simplebot_version,
        help="show program's version number and exit"
    )
    basedir_default = os.environ.get(
        "SIMPLEBOT_BASEDIR", "~/.config/simplebot")
    parser.add_generic_option(
        "--basedir", action="store", metavar="DIR",
        default=basedir_default, type=os.path.expanduser,
        help="directory for storing all simplebot state")
    parser.add_generic_option("--show-ffi", action="store_true",
                              help="show low level ffi events")


@deltabot_hookimpl
def deltabot_init(bot, args):
    if args.show_ffi:
        from deltachat.events import FFIEventLogger
        log = FFIEventLogger(bot.account)
        bot.account.add_account_plugin(log)


class Init:
    """initialize account with emailadr and password.

    This will set and verify smtp/imap connectivity using the provided credentials.
    """
    def add_arguments(self, parser):
        parser.add_argument("emailaddr", metavar="ADDR", type=str)
        parser.add_argument("password", type=str)

    def run(self, bot, args, out):
        if "@" not in args.emailaddr:
            out.fail('invalid email address: {!r}'.format(args.emailaddr))
        success = bot.perform_configure_address(
            args.emailaddr, args.password)
        if not success:
            out.fail(
                'failed to configure with: {}'.format(args.emailaddr))


class Info:
    """show information about configured account."""

    def run(self, bot, args, out):
        if not bot.is_configured():
            out.fail("account not configured, use 'deltabot init'")

        for key, val in bot.account.get_info().items():
            out.line('{:30s}: {}'.format(key, val))


class Serve:
    """serve and react to incoming messages"""

    def run(self, bot, args, out):
        if not bot.is_configured():
            out.fail(
                'account not configured: {}'.format(bot.account.db_path))

        bot.start()
        bot.account.wait_shutdown()


class PluginCmd:
    """bot plugins management."""
    name = 'plugin'
    db_key = 'module-plugins'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list', help='list bot plugins.', action='store_true')
        parser.add_argument(
            '--add', help='add python module(s) paths to be loaded as bot plugin(s). Note that the filesystem paths to the python modules need to be available when the bot starts up.  You can edit the modules after adding them.', metavar="PYMODULE", type=str, nargs='+')
        parser.add_argument(
            '--del', help='delete python module(s) plugin path from bot plugins.', metavar='PYMODULE', dest='_del', type=str, nargs='+')

    def run(self, bot, args, out):
        if args.add:
            self._add(bot, args.add, out)
        elif args._del:
            self._del(bot, args._del, out)
        else:
            for name, plugin in bot.plugins.items():
                out.line('{:25s}: {}'.format(name, plugin))

    def _add(self, bot, pymodules, out):
        existing = list(x for x in bot.get(
            self.db_key, default='').split('\n') if x.strip())
        for pymodule in pymodules:
            assert ',' not in pymodule
            if not os.path.exists(pymodule):
                out.fail('{} does not exist'.format(pymodule))
            path = os.path.abspath(pymodule)
            existing.append(path)

        bot.set(self.db_key, '\n'.join(existing))
        out.line('new python module plugin list:')
        for mod in existing:
            out.line(mod)

    def _del(self, bot, pymodules, out):
        existing = list(x for x in bot.get(
            self.db_key, default='').split('\n') if x.strip())
        remaining = []
        for pymodule in pymodules:
            for p in existing:
                if not p.endswith(pymodule):
                    remaining.append(p)

        bot.set(self.db_key, '\n'.join(remaining))
        out.line('removed {} module(s)'.format(
            len(existing) - len(remaining)))
