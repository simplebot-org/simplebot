
import os
import py
from email.utils import parseaddr
from queue import Queue

import pytest
from _pytest.pytester import LineMatcher

from deltachat.message import Message
from deltachat import account_hookimpl

from .parser import get_base_parser
from .main import make_bot_from_args
from .plugins import make_plugin_manager
from .bot import Replies


@pytest.fixture
def mock_bot(acfactory, request):
    account = acfactory.get_configured_offline_account()
    return make_bot(request, account, request.module)


def make_bot(request, account, plugin_module):
    basedir = os.path.dirname(account.db_path)

    # we use a new plugin manager for each test
    pm = make_plugin_manager()

    # initialize command line
    argv = ["deltabot", "--basedir", basedir]
    parser = get_base_parser(pm, argv=argv)

    args = parser.main_parse_argv(argv)

    bot = make_bot_from_args(args=args, plugin_manager=pm, account=account)

    # we auto-register the (non-builtin) module
    # which contains the test which requested this bot
    if not plugin_module.__name__.startswith("deltabot.builtin."):
        # don't re-register already registered setuptools plugins
        if not pm.is_registered(plugin_module):
            bot.plugins.add_module(plugin_module.__name__, plugin_module)

    # startup bot
    request.addfinalizer(bot.trigger_shutdown)
    bot.start()
    return bot


@pytest.fixture
def mocker(mock_bot):
    class Mocker:
        def __init__(self):
            self.bot = mock_bot
            self.account = mock_bot.account

        def make_incoming_message(self, text, addr="Alice <alice@example.org>"):
            msg = Message.new_empty(self.account, "text")
            msg.set_text(text)
            name, routeable_addr = parseaddr(addr)
            contact = self.account.create_contact(routeable_addr, name=name)
            chat = self.account.create_chat(contact)
            msg_in = chat.prepare_message(msg)
            return msg_in

        def run_command(self, text):
            msg = self.make_incoming_message(text)
            replies = Replies(msg, self.bot.logger)
            self.bot.commands.deltabot_incoming_message(message=msg, replies=replies)
            l = replies.send_reply_messages()
            if not l:
                raise ValueError("no reply for command {!r}".format(text))
            if len(l) > 1:
                raise ValueError("more than one reply for {!r}".format(text))
            return l[0]

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


class CmdlineRunner:
    def __init__(self):
        self._rootargs = ["deltabot"]

    def set_basedir(self, account_dir):
        self._rootargs.append("--basedir={}".format(account_dir))

    def invoke(self, args):
        # create a new plugin manager for each command line invocation
        pm = make_plugin_manager()
        parser = get_base_parser(pm, argv=self._rootargs)
        argv = self._rootargs + args
        code, message = 0, None
        cap = py.io.StdCaptureFD(mixed=True)
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
            raise Exception("got exit code {!r}, expected {!r}, output: {}".format(
                res.exit_code, code, res.output))
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
