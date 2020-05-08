import os
import pytest
import textwrap


@pytest.fixture
def parser(plugin_manager, tmpdir, monkeypatch):
    from deltabot.parser import get_base_parser
    basedir = tmpdir.mkdir("basedir").strpath
    argv = ["deltabot", "--basedir", basedir]
    parser = get_base_parser(plugin_manager, argv=argv)
    assert parser.basedir == basedir
    monkeypatch.setenv("DELTABOT_BASEDIR", basedir)
    return parser


@pytest.fixture
def makeini(parser):
    def makeini(source):
        s = textwrap.dedent(source)
        p = os.path.join(parser.basedir, "deltabot.ini")
        with open(p, "w") as f:
            f.write(s)
        return p

    return makeini


class TestParser:
    def test_generic(self, parser):
        args = parser.main_parse_argv(["deltabot"])
        assert args.command is None

        args = parser.main_parse_argv(["deltabot", "--basedir=123"])
        assert args.basedir == "123"

    def test_add_generic(self, parser, makeini):
        parser.add_generic_option(
            "--example", choices=["info", "debug", "err", "warn"],
            default="info", help="stdout logging level.",
            inipath="section:key")

        makeini("""
            [section]
            key = debug
        """)
        args = parser.main_parse_argv(["deltabot"])
        assert args.example == "debug"


class TestInit:
    def test_noargs(self, parser):
        with pytest.raises(SystemExit) as ex:
            parser.main_parse_argv(["deltabot", "init"])
        assert ex.value.code != 0

    def test_basic_args(self, parser):
        args = parser.main_parse_argv(["deltabot", "init", "email@x.org", "123"])
        assert args.command == "init"
        assert args.emailaddr == "email@x.org"
        assert args.password == "123"

    def test_arg_verification_fails(self, parser):
        args = parser.main_parse_argv(["deltabot", "init", "email", "123"])
        assert args.command == "init"
        assert args.emailaddr == "email"
        assert args.password == "123"
        with pytest.raises(SystemExit) as ex:
            parser.main_run(bot=None, args=args)
        assert ex.value.code != 0

    def test_arg_run_fails(self, parser):
        args = parser.main_parse_argv(["deltabot", "init", "email@example.org", "123"])
        l = []

        class PseudoBot:
            def perform_configure_address(self, emailaddr, password):
                l.append((emailaddr, password))
                return True
        parser.main_run(bot=PseudoBot(), args=args)
        assert l == [("email@example.org", "123")]
