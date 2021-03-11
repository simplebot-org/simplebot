# -*- coding: utf-8 -*-

import os
import shutil
import tempfile
import threading
from typing import Generator, Union

import deltachat as dc
import py
from deltachat import Account, Chat, Contact, Message, account_hookimpl
from deltachat.capi import lib
from deltachat.cutil import as_dc_charpointer
from deltachat.message import parse_system_add_remove
from deltachat.tracker import ConfigureTracker

from .builtin.admin import get_admins
from .builtin.cmdline import PluginCmd
from .commands import Commands, _cmds
from .filters import Filters, _filters
from .plugins import Plugins, get_global_plugin_manager


class Replies:
    def __init__(self, message: Message, logger) -> None:
        self.incoming_message = message
        self.logger = logger
        self._replies = []

    def has_replies(self) -> bool:
        return bool(self._replies)

    def add(self, text: str = None, html: str = None,
            filename: str = None, bytefile=None, sender: str = None,
            quote: Message = None, chat: Chat = None) -> None:
        """ Add a text or file-based reply. """
        if bytefile:
            if not filename:
                raise ValueError("missing filename suggestion, needed with bytefile")
            if os.path.basename(filename) != filename:
                raise ValueError("if bytefile is specified, filename must a basename, not path")

        self._replies.append((text, filename, bytefile, chat, quote, html, sender))

    def send_reply_messages(self) -> list:
        tempdir = tempfile.mkdtemp() if any(x[2] for x in self._replies) else None
        l = []
        try:
            for msg in self._send_replies_to_core(tempdir):
                self.logger.info("reply id={} chat={} sent with text: {!r}".format(
                                 msg.id, msg.chat, msg.text[:50]))
                l.append(msg)
        finally:
            if tempdir:
                shutil.rmtree(tempdir)
        return l

    def _send_replies_to_core(self, tempdir: str) -> Generator[Message, None, None]:
        for text, filename, bytefile, chat, quote, html, sender in self._replies:
            if bytefile:
                # XXX avoid double copy -- core will copy this file another time
                # XXX maybe also avoid loading the file into RAM but it's max 50MB
                filename = os.path.join(tempdir, filename)
                with open(filename, "wb") as f:
                    f.write(bytefile.read())

            if filename:
                view_type = "file"
            else:
                view_type = "text"
            msg = Message.new_empty(self.incoming_message.account, view_type)
            if quote is not None:
                msg.quote = quote
            if text is not None:
                msg.set_text(text)
            if html is not None:
                lib.dc_msg_set_html(msg._dc_msg, as_dc_charpointer(html))
            if filename is not None:
                msg.set_file(filename)
            if sender is not None:
                lib.dc_msg_set_override_sender_name(
                    msg._dc_msg, as_dc_charpointer(sender))
            if chat is None:
                chat = self.incoming_message.chat
            msg = chat.send_msg(msg)
            yield msg

        self._replies[:] = []


class DeltaBot:
    def __init__(self, account: Account, logger, plugin_manager=None,
                 args: tuple = ()) -> None:
        # by default we will use the global instance of the
        # plugin_manager.
        if plugin_manager is None:
            plugin_manager = get_global_plugin_manager()

        #: Account object for creating contacts/groups etc.
        #: see :class:`deltachat.account.Account`
        self.account = account

        self.logger = logger

        #: plugin subsystem for adding/removing plugins and calling plugin hooks
        #: see :class:`simplebot.plugins.Plugins`
        self.plugins = Plugins(logger=logger, plugin_manager=plugin_manager)

        #: commands subsystem for registering/executing commands in incoming messages
        #: see :class:`simplebot.commands.Commands`
        self.commands = Commands(self)

        #: filter subsystem for registering/performing filters on incoming messages
        #: see :class:`simplebot.filters.Filters`
        self.filters = Filters(self)

        # process dc events and turn them into simplebot ones
        self._eventhandler = IncomingEventHandler(self)

        plugin_manager.hook.deltabot_init.call_historic(kwargs=dict(bot=self, args=args))
        # add manually added python modules as plugins
        mods = self.get(PluginCmd.db_key, '').split('\n')
        while mods:
            pymodule = mods.pop(0)
            if os.path.isdir(pymodule) and not os.path.exists(os.path.join(pymodule, '__init__.py')):
                for m in os.listdir(pymodule):
                    m = os.path.join(pymodule, m)
                    if m.endswith('.py') or os.path.isdir(m):
                        mods.append(m)
            elif pymodule:
                if os.path.exists(pymodule):
                    mod = py.path.local(pymodule).pyimport()
                    self.plugins.add_module(
                        name=os.path.basename(pymodule), module=mod)
                else:
                    self.logger.warning('Plugin not found: %s', pymodule)

        for name, function, admin in _cmds:
            self.commands.register(name, function, admin)
        _cmds.clear()

        for name, function in _filters:
            self.filters.register(name, function)
        _filters.clear()

    #
    # API for bot administration
    #
    def is_admin(self, addr: str) -> bool:
        return addr in get_admins(self)

    #
    # API for persistent scoped-key/value settings
    #
    def set(self, name: str, value: str, scope: str = "global") -> str:
        """ Store a bot setting with the given scope. """
        assert "/" not in scope and "/" not in name
        old_val = self.get(name, scope=scope)
        key = scope + "/" + name
        self.plugins._pm.hook.deltabot_store_setting(key=key, value=value)
        return old_val

    def delete(self, name: str, scope: str = "global") -> None:
        """ Delete a bot setting with the given scope. """
        assert "/" not in scope
        key = scope + "/" + name
        self.plugins._pm.hook.deltabot_store_setting(key=key, value=None)

    def get(self, name: str, default: str = None, scope: str = "global") -> str:
        """ Get a bot setting from the given scope. """
        assert "/" not in scope
        key = scope + "/" + name
        res = self.plugins._pm.hook.deltabot_get_setting(key=key)
        return res if res is not None else default

    def list_settings(self, scope: str = None) -> list:
        """ list bot settings for the given scope.

        If scope is not specified, all settings are returned.
        """
        assert scope is None or "/" not in scope
        l = self.plugins._pm.hook.deltabot_list_settings()
        if scope is not None:
            scope_prefix = scope + "/"
            l = [(x[0][len(scope_prefix):], x[1])
                 for x in l if x[0].startswith(scope_prefix)]
        return l

    #
    # API for getting at and creating contacts and chats
    #
    @property
    def self_contact(self) -> Contact:
        """ this bot's contact (with .addr and .display_name attributes). """
        return self.account.get_self_contact()

    def get_contact(self, ref: Union[str, int, Contact]) -> Contact:
        """ return Contact object (create one if needed) for the specified 'ref'.

        ref can be a Contact, email address string or contact id.
        """
        if isinstance(ref, str):
            return self.account.create_contact(ref)
        if isinstance(ref, int):
            return self.account.get_contact_by_id(ref)
        if isinstance(ref, Contact):
            return ref

    def get_chat(self, ref: Union[Message, Contact, str, int]) -> Chat:
        """ Return a 1:1 chat (creating one if needed) from the specified ref object.

        ref can be a Message, Contact, email address string or chat-id integer.
        """
        if isinstance(ref, dc.message.Message):
            return self.account._create_chat_by_message_id(ref.id)
        if isinstance(ref, (dc.contact.Contact, str)):
            return self.account.create_chat(ref)
        if isinstance(ref, int):
            try:
                return self.account.get_chat_by_id(ref)
            except ValueError:
                return None

    def create_group(self, name: str, contacts=[]) -> Chat:
        """ Create a new group chat. """
        return self.account.create_group_chat(name, contacts)

    #
    # configuration related API
    #

    def is_configured(self) -> bool:
        """ Return True if this bot account is successfully configured. """
        return bool(self.account.is_configured())

    def perform_configure_address(self, email: str, password: str) -> bool:
        """ perform initial email/password bot account configuration.  """
        assert not self.is_configured() or self.account.get_config("addr") == email

        self.account.update_config(dict(
            addr=email,
            mail_pw=password,
            bot=1,
            # set some useful bot defaults on the account
            delete_server_after=1,
            delete_device_after=2592000,
            mdns_enabled=0,
            save_mime_headers=1,
            e2ee_enabled=1,
            sentbox_watch=0,
            mvbox_watch=0,
            bcc_self=0
        ))

        tracker = ConfigureTracker(self.account)
        with self.account.temp_plugin(tracker) as configtracker:
            self.account.configure()
            try:
                configtracker.wait_finish()
            except configtracker.ConfigureFailed as ex:
                success = False
                self.logger.error('Failed to configure: {}'.format(ex))
            else:
                success = True
                self.logger.info('Successfully configured {}'.format(email))
            return success

    #
    # start/wait/shutdown API
    #
    def start(self) -> None:
        """ Start bot threads and processing messages. """
        self.plugins.hook.deltabot_start(bot=self)
        addr = self.account.get_config("addr")
        self.logger.info("bot listening at: {}".format(addr))
        self._eventhandler.start()
        self.account.start_io()

    def wait_shutdown(self) -> None:
        """ Wait and block until bot account is shutdown. """
        self.account.wait_shutdown()
        self._eventhandler.stop()

    def trigger_shutdown(self) -> None:
        """ Trigger a shutdown of the bot. """
        self._eventhandler.stop()
        self.plugins.hook.deltabot_shutdown(bot=self)
        self.account.shutdown()


class CheckAll:
    def __init__(self, bot, db) -> None:
        self.bot = bot
        self.db = db

    def perform(self) -> None:
        logger = self.bot.logger
        logger.info("CheckAll perform-loop start")
        for msg_id in self.db.get_msgs():
            try:
                message = self.bot.account.get_message_by_id(msg_id)
                headers = message.get_mime_headers() or dict()
                if 'Chat-Version' in headers or message.is_encrypted():
                    replies = Replies(message, logger=logger)
                    logger.info(
                        "processing incoming fresh message id={}".format(
                            message.id))
                    if message.is_system_message():
                        self.handle_system_message(message, replies)
                    elif not message.get_sender_contact().is_blocked():
                        self.bot.plugins.hook.deltabot_incoming_message(
                            message=message,
                            bot=self.bot,
                            replies=replies
                        )
                    replies.send_reply_messages()
                else:
                    logger.debug("ignoring classic email id=%s", msg_id)
                logger.info(
                    "processing message id={} FINISHED".format(msg_id))
            except Exception as ex:
                logger.exception(
                    "processing message={} failed: {}".format(msg_id, ex))
            self.db.pop_msg(msg_id)
        logger.info("CheckAll perform-loop finish")

    def handle_system_message(self, message: Message, replies: Replies) -> None:
        logger = self.bot.logger
        res = parse_system_add_remove(message.text)
        if res is None:
            logger.info("ignoring system message id={} text: {}".format(
                message.id, message.text))
            return

        action, affected, actor = res
        hook_name = "deltabot_member_{}".format(action)
        meth = getattr(self.bot.plugins.hook, hook_name)
        logger.info("calling hook {}".format(hook_name))
        meth(message=message, replies=replies, chat=message.chat,
             actor=self.bot.account.create_contact(actor), bot=self.bot,
             contact=self.bot.account.create_contact(affected))


class IncomingEventHandler:
    def __init__(self, bot) -> None:
        self.bot = bot
        self.logger = bot.logger
        self.plugins = bot.plugins
        self.bot.account.add_account_plugin(self)
        self._needs_check = threading.Event()
        self._needs_check.set()
        self._running = True

    def start(self) -> None:
        self.logger.info("starting bot-event-handler THREAD")
        self.db = self.bot.plugins._pm.get_plugin(name='db')
        self._thread = t = threading.Thread(target=self.event_worker, name="bot-event-handler", daemon=True)
        t.start()

    def stop(self) -> None:
        self._running = False
        self._needs_check.set()
        self._thread.join(timeout=10)

    def event_worker(self) -> None:
        self.logger.debug("event-worker startup")
        while self._running:
            self._needs_check.wait()
            self._needs_check.clear()
            CheckAll(self.bot, self.db).perform()

    @account_hookimpl
    def ac_incoming_message(self, message: Message) -> None:
        # we always accept incoming messages to remove the need  for
        # bot authors to having to deal with deaddrop/contact requests.
        message.create_chat()
        self.logger.info("incoming message from {} id={} chat={} text={!r}".format(
            message.get_sender_contact().addr,
            message.id, message.chat.id, message.text[:50]))

        self.db.put_msg(message.id)
        # message is now in DB, schedule a check
        self._needs_check.set()

    # @account_hookimpl
    # def ac_chat_modified(self, message):
    #     self.db.put_msg(message.id)
    #     self._needs_check.set()

    @account_hookimpl
    def ac_member_removed(self, message: Message) -> None:
        self.db.put_msg(message.id)
        self._needs_check.set()

    @account_hookimpl
    def ac_member_added(self, message: Message) -> None:
        self.db.put_msg(message.id)
        self._needs_check.set()

    @account_hookimpl
    def ac_message_delivered(self, message: Message) -> None:
        self.logger.info("message id={} chat={} delivered to smtp".format(
            message.id, message.chat.id))