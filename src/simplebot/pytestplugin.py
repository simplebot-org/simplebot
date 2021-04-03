import os
import re
from email.utils import parseaddr
from queue import Queue
from typing import Union

import py
import pytest
from _pytest.pytester import LineMatcher
from deltachat import account_hookimpl
from deltachat.chat import Chat
from deltachat.message import Message

from .bot import Replies
from .main import make_bot_from_args
from .parser import get_base_parser
from .plugins import make_plugin_manager


@pytest.fixture
def mock_stopped_bot(acfactory, request):
    account = acfactory.get_configured_offline_account()
    return make_bot(request, account, request.module, False)


@pytest.fixture
def mock_bot(acfactory, request):
    account = acfactory.get_configured_offline_account()
    return make_bot(request, account, request.module)


def make_bot(request, account, plugin_module, started=True):
    basedir = os.path.dirname(account.db_path)

    # we use a new plugin manager for each test
    pm = make_plugin_manager()

    argv = ["simplebot", "--stdlog=debug", "--account", basedir]

    # initialize command line
    parser = get_base_parser(pm, argv)
    args = parser.main_parse_argv(argv)

    bot = make_bot_from_args(args=args, plugin_manager=pm, account=account)

    # we auto-register the (non-builtin) module
    # which contains the test which requested this bot
    if not plugin_module.__name__.startswith("simplebot.builtin."):
        # don't re-register already registered setuptools plugins
        if not pm.is_registered(plugin_module):
            bot.plugins.add_module(plugin_module.__name__, plugin_module)

    # startup bot
    request.addfinalizer(bot.trigger_shutdown)
    if started:
        bot.start()
    return bot


@pytest.fixture
def mocker(mock_bot):
    class Mocker:
        def __init__(self) -> None:
            self.bot = mock_bot
            self.account = mock_bot.account

        def make_incoming_message(
            self,
            text: str = None,
            html: str = None,
            filename: str = None,
            viewtype: str = None,
            group: Union[str, Chat] = None,
            impersonate: str = None,
            addr: str = "Alice <alice@example.org>",
            quote: Message = None,
        ) -> Message:
            if filename and not os.path.exists(filename):
                filename = os.path.join(self.bot.account.get_blobdir(), filename)
                with open(filename, "wb"):
                    pass

            msg = Replies(self.bot, self.bot.logger)._create_message(
                text=text,
                html=html,
                viewtype=viewtype,
                filename=filename,
                quote=quote,
                sender=impersonate,
            )

            name, routeable_addr = parseaddr(addr)
            contact = self.account.create_contact(routeable_addr, name=name)
            if isinstance(group, Chat):
                chat = group
            elif isinstance(group, str):
                chat = self.account.create_group_chat(group, contacts=[contact])
            else:
                chat = self.account.create_chat(contact)
            msg_in = chat.prepare_message(msg)

            class MsgWrapper:
                def __init__(self, msg, quote, contact):
                    self.msg = msg
                    self.quote = quote
                    self.get_sender_contact = lambda: contact

                def __getattr__(self, name):
                    return self.msg.__getattribute__(name)

                def __setattr__(self, name, value):
                    if name in ("quote", "msg", "error"):
                        super().__setattr__(name, value)
                    else:
                        setattr(self.msg, name, value)

            return MsgWrapper(msg_in, quote, contact)

        def get_one_reply(
            self,
            text: str = None,
            html: str = None,
            filename: str = None,
            viewtype: str = None,
            group: Union[str, Chat] = None,
            impersonate: str = None,
            addr: str = "Alice <alice@example.org>",
            quote: Message = None,
            filters: str = None,
            msg: Message = None,
        ) -> Message:
            l = self.get_replies(
                text=text,
                html=html,
                filename=filename,
                viewtype=viewtype,
                group=group,
                impersonate=impersonate,
                addr=addr,
                quote=quote,
                filters=filters,
                msg=msg,
            )
            if not l:
                raise ValueError("no reply for message {!r}".format(text))
            if len(l) > 1:
                raise ValueError(
                    "more than one reply for {!r}, replies={}".format(text, l)
                )
            return l[0]

        def get_replies(
            self,
            text: str = None,
            html: str = None,
            filename: str = None,
            viewtype: str = None,
            group: Union[str, Chat] = None,
            impersonate: str = None,
            addr: str = "Alice <alice@example.org>",
            quote: Message = None,
            filters: str = None,
            msg: Message = None,
        ) -> list:
            if filters:
                regex = re.compile(filters)
                for name in list(self.bot.filters._filter_defs.keys()):
                    if not regex.match(name):
                        del self.bot.filters._filter_defs[name]
            if not msg:
                msg = self.make_incoming_message(
                    text=text,
                    html=html,
                    filename=filename,
                    viewtype=viewtype,
                    group=group,
                    impersonate=impersonate,
                    addr=addr,
                    quote=quote,
                )
            replies = Replies(msg, self.bot.logger)
            self.bot.plugins.hook.deltabot_incoming_message(
                message=msg, replies=replies, bot=self.bot
            )
            return replies.send_reply_messages()

    return Mocker()


@pytest.fixture
def bot_tester(acfactory, request):
    ac1, ac2 = acfactory.get_two_online_accounts()
    bot = make_bot(request, ac2, request.module)
    return BotTester(ac1, bot)


class BotTester:
    def __init__(self, send_account, bot):
        self.send_account = send_account
        self.send_account.set_config("displayname", "bot-tester")
        self.own_addr = self.send_account.get_config("addr")
        self.own_displayname = self.send_account.get_config("displayname")

        self.send_account.add_account_plugin(self)
        self.bot = bot
        bot_addr = bot.account.get_config("addr")
        self.bot_contact = self.send_account.create_contact(bot_addr)
        self.bot_chat = self.send_account.create_chat(self.bot_contact)
        self._replies = Queue()

    @account_hookimpl
    def ac_incoming_message(self, message):
        message.get_sender_contact().create_chat()
        print("queuing ac_incoming message {}".format(message))
        self._replies.put(message)

    def send_command(self, text):
        self.bot_chat.send_text(text)
        return self.get_next_incoming()

    def get_next_incoming(self):
        reply = self._replies.get(timeout=30)
        print("get_next_incoming got reply text: {}".format(reply.text))
        return reply


@pytest.fixture
def plugin_manager():
    return make_plugin_manager()


@pytest.fixture
def examples(request):
    p = request.fspath.dirpath().dirpath().join("examples")
    if not p.exists():
        pytest.skip("could not locate examples dir at {}".format(p))
    return p


class CmdlineRunner:
    def __init__(self):
        self._rootargs = ["simplebot"]

    def set_basedir(self, account_dir):
        self._rootargs.append("--account={}".format(account_dir))

    def invoke(self, args):
        # create a new plugin manager for each command line invocation
        cap = py.io.StdCaptureFD(mixed=True)
        pm = make_plugin_manager()
        parser = get_base_parser(pm, argv=self._rootargs)
        argv = self._rootargs + args
        code, message = 0, None
        try:
            try:
                args = parser.main_parse_argv(argv)
                bot = make_bot_from_args(args=args, plugin_manager=pm)
                parser.main_run(bot=bot, args=args)
                code = 0
            except SystemExit as ex:
                code = ex.code
                message = str(ex)
            # pass through unexpected exceptions
            # except Exception as ex:
            #    code = 127
            #    message = str(ex)
        finally:
            output, _ = cap.reset()
        return InvocationResult(code, message, output)

    def run_ok(self, args, fnl=None):
        __tracebackhide__ = True
        res = self.invoke(args)
        if res.exit_code != 0:
            print(res.output)
            raise Exception("cmd exited with %d: %s" % (res.exit_code, args))
        return _perform_match(res.output, fnl)

    def run_fail(self, args, fnl=None, code=None):
        __tracebackhide__ = True
        res = self.invoke(args)
        if res.exit_code == 0 or (code is not None and res.exit_code != code):
            print(res.output)
            raise Exception(
                "got exit code {!r}, expected {!r}, output: {}".format(
                    res.exit_code, code, res.output
                )
            )
        return _perform_match(res.output, fnl)


class InvocationResult:
    def __init__(self, code, message, output):
        self.exit_code = code
        self.message = message
        self.output = output


def _perform_match(output, fnl):
    __tracebackhide__ = True
    if fnl:
        lm = LineMatcher(output.splitlines())
        lines = [x.strip() for x in fnl.strip().splitlines()]
        try:
            lm.fnmatch_lines(lines)
        except Exception:
            print(output)
            raise
    return output


@pytest.fixture
def cmd():
    """ invoke a command line subcommand with a unique plugin manager. """
    return CmdlineRunner()


@pytest.fixture
def mycmd(cmd, tmpdir, request):
    cmd.set_basedir(tmpdir.mkdir("account").strpath)
    return cmd
