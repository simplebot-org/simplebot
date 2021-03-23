# PYTHON_ARGCOMPLETE_OK

import argparse
import inspect
import os

import py

from .utils import get_account_path, get_default_account

main_description = """
The simplebot command line offers sub commands for initialization, configuration
and web-serving of Delta Chat Bots.  New sub commands may be added via plugins.
"""


class MyArgumentParser(argparse.ArgumentParser):
    class ArgumentError(Exception):
        """ an error from the argparse subsystem. """

    def error(self, error) -> None:
        """raise errors instead of printing and raising SystemExit"""
        raise self.ArgumentError(error)

    def add_generic_option(self, *flags, **kwargs) -> None:
        """ add a generic argument option. """
        if not hasattr(self, "subparsers"):
            raise ValueError("can not add generic option to sub command")
        if not (flags and flags[0].startswith("-")):
            raise ValueError("can not generically add positional args")
        inipath = kwargs.pop("inipath", None)
        action = self.generic_options.add_argument(*flags, **kwargs)
        action.inipath = inipath

    def add_subcommand(self, cls) -> None:
        """ Add a subcommand to simplebot. """
        if not hasattr(self, "subparsers"):
            raise ValueError("can not add sub command to subcommand")
        doc, description = parse_docstring(cls.__doc__)
        name = getattr(cls, "name", None)
        if name is None:
            name = cls.__name__.lower()
        subparser = self.subparsers.add_parser(
            name=name, description=description, help=doc
        )
        subparser.Action = argparse.Action

        inst = cls()
        meth = getattr(inst, "add_arguments", None)
        if meth is not None:
            meth(parser=subparser)
        subparser.set_defaults(subcommand_instance=inst)

    def _merge_ini(self) -> None:
        if not self.basedir:
            return
        p = os.path.join(self.basedir, "bot.ini")
        if os.path.exists(p):
            cfg = py.iniconfig.IniConfig(p)
            for action in self._actions:
                if getattr(action, "inipath", None):
                    section, key = action.inipath.split(":")
                    default = cfg.get(section, key)
                    if default:
                        action.default = default

    def main_parse_argv(self, argv):
        try_argcomplete(self)
        self._merge_ini()
        try:
            args = self.parse_args(argv[1:])
            args.basedir = self.basedir
            return args
        except self.ArgumentError as e:
            if not argv[1:]:
                return self.parse_args(["-h"])
            self.print_usage()
            self.exit(2, "%s: error: %s\n" % (self.prog, e.args[0]))

    def main_run(self, bot, args) -> None:
        try:
            if args.command is None:
                self.out.line(self.format_usage())
                self.out.line(self.description.strip())
                self.out.line()
                for name, p in self.subparsers.choices.items():
                    self.out.line(
                        "{:20s} {}".format(name, p.description.split("\n")[0].strip())
                    )
                self.out.line()
                self.out.ok_finish("please specify a subcommand", red=True)

            funcargs = set(inspect.getargs(args.subcommand_instance.run.__code__).args)
            if not bot and "bot" in funcargs:
                msg = 'No default account is set so "--account" argument is required to use "{}" subcommand.'.format(
                    args.command
                )
                self.out.fail(msg)
            kwargs = dict(bot=bot, args=args, out=self.out)
            for key in list(kwargs.keys()):
                if key not in funcargs:
                    del kwargs[key]
            res = args.subcommand_instance.run(**kwargs)
        except ValueError as ex:
            res = str(ex)
        if res:
            self.out.fail(str(res))


class CmdlineOutput:
    def __init__(self) -> None:
        self.tw = py.io.TerminalWriter()

    def line(self, message="", **kwargs) -> None:
        self.tw.line(message, **kwargs)

    def fail(self, message) -> None:
        self.tw.line("FAIL: {}".format(message), red=True)
        raise SystemExit(1)

    def ok_finish(self, message, **kwargs) -> None:
        self.line(message, **kwargs)
        raise SystemExit(0)


def try_argcomplete(parser) -> None:
    if os.environ.get("_ARGCOMPLETE"):
        try:
            import argcomplete
        except ImportError:
            pass
        else:
            argcomplete.autocomplete(parser)


def get_base_parser(plugin_manager, argv) -> MyArgumentParser:
    parser = MyArgumentParser(prog="simplebot", description=main_description)
    parser.plugin_manager = plugin_manager
    parser.subparsers = parser.add_subparsers(dest="command")
    parser.generic_options = parser.add_argument_group("generic options")
    parser.out = CmdlineOutput()
    plugin_manager.hook.deltabot_init_parser(parser=parser)

    # preliminary get the basedir
    args, remaining = parser.parse_known_args(argv[1:])
    if not args.basedir:
        if args.command == "init":
            args.basedir = get_account_path(args.emailaddr)
        else:
            addr = get_default_account()
            args.basedir = addr and get_account_path(addr)
            if args.basedir and not os.path.exists(args.basedir):
                args.basedir = None
    parser.basedir = args.basedir

    return parser


def parse_docstring(txt) -> tuple:
    description = txt
    i = txt.find(".")
    if i == -1:
        doc = txt
    else:
        doc = txt[: i + 1]
    return doc, description
