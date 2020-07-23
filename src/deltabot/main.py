
import os
import sys

from deltachat import Account

from .plugins import get_global_plugin_manager
from .parser import get_base_parser, MyArgumentParser
from .bot import DeltaBot


def main(argv=None):
    """delta.chat bot management command line interface."""
    pm = get_global_plugin_manager()
    if argv is None:
        argv = sys.argv
    try:
        parser = get_base_parser(plugin_manager=pm, argv=argv)
        args = parser.main_parse_argv(argv)
    except MyArgumentParser.ArgumentError as ex:
        print(str(ex), file=sys.stderr)
        sys.exit(1)
    bot = make_bot_from_args(args, plugin_manager=pm)
    parser.main_run(bot=bot, args=args)


def make_bot_from_args(args, plugin_manager, account=None):
    basedir = os.path.abspath(os.path.expanduser(args.basedir))
    if not os.path.exists(basedir):
        os.makedirs(basedir)

    if account is None:
        db_path = os.path.join(basedir, "account.db")
        account = Account(db_path, "deltabot/{}".format(sys.platform))

    logger = plugin_manager.hook.deltabot_get_logger(args=args)
    return DeltaBot(account, logger, plugin_manager=plugin_manager, args=args)
