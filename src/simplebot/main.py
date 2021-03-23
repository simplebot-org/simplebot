import os
import sys
from typing import Optional

from deltachat import Account

from .bot import DeltaBot
from .parser import MyArgumentParser, get_base_parser
from .plugins import get_global_plugin_manager


def main(argv=None) -> None:
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


def make_bot_from_args(args, plugin_manager, account=None) -> Optional[DeltaBot]:
    if not args.basedir:
        return None
    if not os.path.exists(args.basedir):
        os.makedirs(args.basedir)

    if account is None:
        db_path = os.path.join(args.basedir, "account.db")
        account = Account(db_path, "simplebot/{}".format(sys.platform))

    logger = plugin_manager.hook.deltabot_get_logger(args=args)
    return DeltaBot(account, logger, plugin_manager=plugin_manager, args=args)
