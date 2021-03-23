import os
import textwrap

import pytest


@pytest.fixture
def parser(plugin_manager, tmpdir, monkeypatch):
    from simplebot.parser import get_base_parser

    basedir = tmpdir.mkdir("basedir").strpath
    argv = ["simplebot", "--account", basedir]
    parser = get_base_parser(plugin_manager, argv)
    assert parser.basedir == basedir
    monkeypatch.setenv("SIMPLEBOT_ACCOUNT", basedir)
    return parser


@pytest.fixture
def makeini(parser, monkeypatch):
    def makeini(source):
        s = textwrap.dedent(source)
        p = os.path.join(parser.basedir, "bot.ini")
        with open(p, "w") as f:
            f.write(s)
        return p

    return makeini


class TestParser:
    def test_generic(self, plugin_manager):
        from simplebot.parser import get_base_parser

        basedir = "/123"
        argv = ["simplebot", "--account", basedir]
        parser = get_base_parser(plugin_manager, argv)

        args = parser.main_parse_argv(argv)
        assert args.basedir == basedir

        args = parser.main_parse_argv(["simplebot"])
        assert args.command is None

    def test_add_generic(self, parser, makeini):
        parser.add_generic_option(
            "--example",
            choices=["info", "debug", "err", "warn"],
            default="info",
            help="stdout logging level.",
            inipath="section:key",
        )

        makeini(
            """
            [section]
            key = debug
        """
        )
        args = parser.main_parse_argv(["simplebot"])
        assert args.example == "debug"


class TestInit:
    def test_noargs(self, parser):
        with pytest.raises(SystemExit) as ex:
            parser.main_parse_argv(["simplebot", "init"])
        assert ex.value.code != 0

    def test_basic_args(self, parser):
        args = parser.main_parse_argv(["simplebot", "init", "email@x.org", "123"])
        assert args.command == "init"
        assert args.emailaddr == "email@x.org"
        assert args.password == "123"

    def test_arg_verification_fails(self, parser):
        args = parser.main_parse_argv(["simplebot", "init", "email", "123"])
        assert args.command == "init"
        assert args.emailaddr == "email"
        assert args.password == "123"
        with pytest.raises(SystemExit) as ex:
            parser.main_run(bot=None, args=args)
        assert ex.value.code != 0

    def test_arg_run_fails(self, parser):
        args = parser.main_parse_argv(["simplebot", "init", "email@example.org", "123"])
        l = []

        class PseudoBot:
            def perform_configure_address(self, emailaddr, password):
                l.append((emailaddr, password))
                return True

        parser.main_run(bot=PseudoBot(), args=args)
        assert l == [("email@example.org", "123")]
