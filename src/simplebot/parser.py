# PYTHON_ARGCOMPLETE_OK

import argparse
import os

import py

main_description = """
The deltabot command line offers sub commands for initialization, configuration
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
            name=name,
            description=description,
            help=doc
        )
        subparser.Action = argparse.Action

        inst = cls()
        meth = getattr(inst, "add_arguments", None)
        if meth is not None:
            meth(parser=subparser)
        subparser.set_defaults(subcommand_instance=inst)

    def _merge_ini(self) -> None:
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
            return self.parse_args(argv[1:])
        except self.ArgumentError as e:
            if not argv[1:]:
                return self.parse_args(["-h"])
            self.print_usage()
            self.exit(2, "%s: error: %s\n" % (self.prog, e.args[0]))

    def main_run(self, bot, args) -> None:
        out = CmdlineOutput()

        if args.command is None:
            out.line(self.format_usage())
            out.line(self.description.strip())
            out.line()
            for name, p in self.subparsers.choices.items():
                out.line("{:20s} {}".format(name, p.description.split("\n")[0].strip()))
            out.line()
            out.ok_finish("please specify a subcommand", red=True)

        try:
            res = args.subcommand_instance.run(bot=bot, args=args, out=out)
        except ValueError as ex:
            res = str(ex)
        if res:
            out.fail(str(res))


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
    if os.environ.get('_ARGCOMPLETE'):
        try:
            import argcomplete
        except ImportError:
            pass
        else:
            argcomplete.autocomplete(parser)


def get_base_parser(plugin_manager, argv):
    parser = MyArgumentParser(prog="simplebot", description=main_description)
    parser.plugin_manager = plugin_manager
    parser.subparsers = parser.add_subparsers(dest="command")
    parser.generic_options = parser.add_argument_group("generic options")
    plugin_manager.hook.deltabot_init_parser(parser=parser)

    # preliminary set the basedir on the parser
    args, remaining = parser.parse_known_args(argv[1:])
    parser.basedir = args.basedir
    return parser


def parse_docstring(txt) -> tuple:
    description = txt
    i = txt.find(".")
    if i == -1:
        doc = txt
    else:
        doc = txt[:i + 1]
    return doc, description
