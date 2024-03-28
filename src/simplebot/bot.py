import json
import os
import threading
from tempfile import NamedTemporaryFile
from typing import Any, Generator, List, Optional, Union

import deltachat as dc
import py
from deltachat import Account, Chat, Contact, Message, account_hookimpl
from deltachat.capi import lib
from deltachat.cutil import from_dc_charpointer
from deltachat.events import FFIEvent
from deltachat.message import parse_system_add_remove

from .builtin.admin import add_admin, del_admin, get_admins
from .builtin.cmdline import PluginCmd
from .commands import Commands, _cmds
from .filters import Filters, _filters
from .plugins import Plugins, get_global_plugin_manager
from .templates import help_template
from .utils import (
    StatusUpdateMessage,
    parse_system_image_changed,
    parse_system_title_changed,
    set_builtin_avatar,
)


class Replies:
    def __init__(self, message: Message, logger) -> None:
        self.incoming_message = message
        self.logger = logger
        self._replies: List[tuple] = []

    def has_replies(self) -> bool:
        return bool(self._replies)

    def add(
        self,
        text: str = None,
        *,
        html: str = None,
        viewtype: str = None,
        filename: str = None,
        bytefile=None,
        sender: str = None,
        quote: Message = None,
        chat: Chat = None,
    ) -> None:
        """Schedule a reply message.

        :param text: a text message to include in the reply.
        :param html: an html body to include in the reply message.
        :param viewtype: the message's view type.
        :param filename: a path to a file to be attached to the reply.
        :param bytefile: a byte file object, if present, filename must be
                         specified and sould be the name of the file the
                         file object represents, the file will be attached
                         to the reply message.
        :param sender: if present, the bot will impersonate the given name.
        :param quote: a Message object the reply will quote.
        :param chat: the chat where the reply will be sent, default is the
                     same chat of the message that triggered this reply.
        """
        if bytefile:
            if not filename:
                raise ValueError("missing filename suggestion, needed with bytefile")
            if os.path.basename(filename) != filename:
                raise ValueError(
                    "if bytefile is specified, filename must a basename, not path"
                )

        self._replies.append(
            (text, html, viewtype, filename, bytefile, sender, quote, chat)
        )

    def send_reply_messages(self) -> list:
        l = []
        for msg in self._send_replies_to_core():
            self.logger.debug(
                f"reply id={msg.id} chat={msg.chat} sent with text: {msg.text[:50]!r}"
            )
            l.append(msg)
        return l

    def _send_replies_to_core(self) -> Generator[Message, None, None]:
        for (
            text,
            html,
            viewtype,
            filename,
            bytefile,
            sender,
            quote,
            chat,
        ) in self._replies:
            msg = self._create_message(
                text, html, viewtype, filename, bytefile, sender, quote
            )
            if chat is None:
                chat = self.incoming_message.chat
            msg = chat.send_msg(msg)
            yield msg

        self._replies[:] = []

    def _create_message(
        self,
        text: str = None,
        html: str = None,
        viewtype: str = None,
        filename: str = None,
        bytefile=None,
        sender: str = None,
        quote: Message = None,
    ) -> Message:
        if bytefile:
            assert filename is not None, "bytefile given but filename not provided"
            blobdir = self.incoming_message.account.get_blobdir()
            parts = filename.split(".", maxsplit=1)
            if len(parts) == 2:
                prefix, suffix = parts
                prefix += "-"
                suffix = "." + suffix
            else:
                prefix = filename + "-"
                suffix = None
            with NamedTemporaryFile(
                dir=blobdir, prefix=prefix, suffix=suffix, delete=False
            ) as fp:
                filename = fp.name
            with open(filename, "wb") as f:
                with bytefile:
                    f.write(bytefile.read())

        if not viewtype:
            if filename:
                viewtype = "file"
            else:
                viewtype = "text"
        msg = Message.new_empty(self.incoming_message.account, viewtype)

        if quote is not None:
            msg.quote = quote
        if text:
            msg.set_text(text)
        if html:
            msg.set_html(html)
        if filename:
            msg.set_file(filename)
        if sender:
            msg.set_override_sender_name(sender)

        return msg


class DeltaBot:
    def __init__(
        self, account: Account, logger, plugin_manager=None, args: tuple = ()
    ) -> None:
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

        plugin_manager.hook.deltabot_init.call_historic(
            kwargs=dict(bot=self, args=args)
        )

        # register /help command
        self.commands.register(func=self._help, name="/help")

        # add manually added python modules as plugins
        mods = self.get(PluginCmd.db_key, "").split("\n")
        while mods:
            pymodule = mods.pop(0)
            if os.path.isdir(pymodule) and not os.path.exists(
                os.path.join(pymodule, "__init__.py")
            ):
                for m in os.listdir(pymodule):
                    m = os.path.join(pymodule, m)
                    if m.endswith(".py") or os.path.isdir(m):
                        mods.append(m)
            elif pymodule:
                if os.path.exists(pymodule):
                    mod = py.path.local(pymodule).pyimport()
                    self.plugins.add_module(name=os.path.basename(pymodule), module=mod)
                else:
                    self.logger.warning("Plugin not found: %s", pymodule)

        for items in _cmds:
            self.commands.register(**dict(items))

        for items in _filters:
            self.filters.register(**dict(items))

    #
    # API for bot administration
    #
    def is_admin(self, contact: Union[Contact, int, str]) -> bool:
        """True if the given contact is registered as bot administrator."""
        if isinstance(contact, str):
            addr = contact
        elif isinstance(contact, Contact):
            addr = contact.addr
        else:
            addr = self.get_contact(contact).addr
        return addr in get_admins(self)

    def add_admin(self, contact: Union[Contact, int, str]) -> None:
        """Register contact as bot administrator."""
        if isinstance(contact, str):
            addr = contact
        elif isinstance(contact, Contact):
            addr = contact.addr
        else:
            addr = self.get_contact(contact).addr
        add_admin(self, addr)

    def del_admin(self, contact: Union[Contact, int, str]) -> None:
        """Remove contact from bot administrators."""
        if isinstance(contact, str):
            addr = contact
        elif isinstance(contact, Contact):
            addr = contact.addr
        else:
            addr = self.get_contact(contact).addr
        del_admin(self, addr)

    #
    # API for persistent scoped-key/value settings
    #
    def set(self, name: str, value: str, scope: str = "global") -> str:
        """Store a bot setting with the given scope."""
        assert "/" not in scope and "/" not in name
        old_val = self.get(name, scope=scope)
        key = scope + "/" + name
        self.plugins.hook.deltabot_store_setting(key=key, value=value)
        return old_val

    def delete(self, name: str, scope: str = "global") -> None:
        """Delete a bot setting with the given scope."""
        assert "/" not in scope
        key = scope + "/" + name
        self.plugins.hook.deltabot_store_setting(key=key, value=None)

    def get(
        self, name: str, default: str = None, scope: str = "global"
    ) -> Optional[str]:
        """Get a bot setting from the given scope."""
        assert "/" not in scope
        key = scope + "/" + name
        res = self.plugins.hook.deltabot_get_setting(key=key)
        return res if res is not None else default

    def list_settings(self, scope: str = None) -> list:
        """list bot settings for the given scope.

        If scope is not specified, all settings are returned.
        """
        assert scope is None or "/" not in scope
        l = self.plugins.hook.deltabot_list_settings()
        if scope is not None:
            scope_prefix = scope + "/"
            l = [
                (x[0][len(scope_prefix) :], x[1])
                for x in l
                if x[0].startswith(scope_prefix)
            ]
        return l

    def add_preference(self, name: str, description: str) -> None:
        """add a preference users can set with /set command.

        The given description will be shown to the users.
        """
        assert description is not None
        self.set(name, description, scope="preferences")

    def get_preference_description(self, name: str) -> Optional[str]:
        """Return preference description or None if the preference doesn't exist."""
        return self.get(name, scope="preferences")

    def delete_preference(self, name: str) -> None:
        """delete a preference, it will no longer be available to users."""
        self.delete(name, scope="preferences")

    def get_preferences(self) -> List[tuple]:
        """get list of preferences available to users."""
        return self.list_settings(scope="preferences")

    #
    # API for getting at and creating contacts and chats
    #
    @property
    def self_contact(self) -> Contact:
        """this bot's contact (with .addr and .display_name attributes)."""
        return self.account.get_self_contact()

    def get_contact(self, ref: Union[str, int, Contact]) -> Contact:
        """return Contact object (create one if needed) for the specified 'ref'.

        ref can be a Contact, email address string or contact id.
        """
        if isinstance(ref, str):
            return self.account.create_contact(ref)
        if isinstance(ref, int):
            return self.account.get_contact_by_id(ref)
        if isinstance(ref, Contact):
            return ref

    def get_chat(self, ref: Union[Message, Contact, str, int]) -> Chat:
        """Return a 1:1 chat (creating one if needed) from the specified ref object.

        ref can be a Message, Contact, email address string or chat-id integer.
        """
        if isinstance(ref, dc.message.Message):
            return ref.chat
        if isinstance(ref, (dc.contact.Contact, str)):
            return self.account.create_chat(ref)
        if isinstance(ref, int):
            try:
                return self.account.get_chat_by_id(ref)
            except ValueError:
                return None

    def create_group(self, name: str, contacts: list = None) -> Chat:
        """Create a new group chat."""
        return self.account.create_group_chat(name, contacts or [])

    #
    # configuration related API
    #

    def is_configured(self) -> bool:
        """Return True if this bot account is successfully configured."""
        return bool(self.account.is_configured())

    def perform_configure_address(self, email: str, password: str, **kwargs) -> bool:
        """perform initial email/password bot account configuration."""
        assert not self.is_configured() or self.account.get_config("addr") == email

        configs = dict(
            addr=email,
            mail_pw=password,
            bot=1,
            # set some useful bot defaults on the account
            delete_server_after=1,
            delete_device_after=2592000,
            save_mime_headers=1,
            sentbox_watch=0,
            bcc_self=0,
            selfstatus="I'm a Delta Chat bot 🤖. Send me /help for more info.\n\nSource code: https://github.com/simplebot-org/simplebot",
            **kwargs,
        )
        self.account.update_config(configs)

        configtracker = self.account.configure()
        try:
            configtracker.wait_finish()
        except configtracker.ConfigureFailed as ex:
            success = False
            self.logger.error("Failed to configure: %s", ex)
        else:
            set_builtin_avatar(self)
            success = True
            self.logger.info("Successfully configured %s", email)
        return success

    #
    # start/wait/shutdown API
    #
    def start(self) -> None:
        """Start bot threads and processing messages."""
        self.plugins.hook.deltabot_start(bot=self)
        addr = self.account.get_config("addr")
        self.logger.info("bot listening at: %s", addr)
        self._eventhandler.start()
        self.account.start_io()

    def wait_shutdown(self) -> None:
        """Wait and block until bot account is shutdown."""
        self.account.wait_shutdown()
        self._eventhandler.stop()

    def trigger_shutdown(self) -> None:
        """Trigger a shutdown of the bot."""
        self._eventhandler.stop()
        self.plugins.hook.deltabot_shutdown(bot=self)
        self.account.shutdown()

    #
    # help command
    #
    def _help(self, bot, command, replies) -> None:
        """get the bot's help."""
        is_admin = bot.is_admin(command.message.get_sender_contact().addr)

        cmds = []
        has_prefs = bool(bot.get_preferences())
        for c in self.commands._cmd_defs.values():
            if not c.hidden and (not c.admin or is_admin):
                if c.cmd != "/set" or has_prefs:
                    cmds.append(c)
        cmds.sort(key=lambda c: c.cmd)

        filters = []
        for f in self.filters._filter_defs.values():
            if not f.hidden and (not f.admin or is_admin):
                filters.append(f)
        filters.sort(key=lambda f: f.name)

        plugins = []
        for plug, _ in bot.plugins._pm.list_plugin_distinfo():
            plugins.append(bot.plugins._pm.get_name(plug))
        plugins.sort()

        html = help_template.render(
            addr=bot.self_contact.addr, cmds=cmds, filters=filters, plugins=plugins
        )
        replies.add(text="ℹ️ Help", html=html)


class CheckAll:
    def __init__(self, bot, db) -> None:
        self.bot = bot
        self.db = db

    def perform(self) -> None:
        logger = self.bot.logger
        logger.debug("CheckAll perform-loop start")
        for msg_str in self.db.get_msgs():
            try:
                try:
                    msg_id = int(msg_str)
                except ValueError:
                    msg_id = 0
                if msg_id:
                    self.process_msg_id(msg_id)
                else:
                    self.process_status_update(json.loads(msg_str))
            except Exception as ex:
                logger.exception("processing message=%s failed: %s", msg_str, ex)
            self.db.pop_msg(msg_str)
        logger.debug("CheckAll perform-loop finish")

    def process_status_update(self, update: dict) -> None:
        logger = self.bot.logger
        logger.info(
            "processing incoming status update (msg=%s, serial=%s)",
            update["msg_id"],
            update["serial"],
        )

        message = StatusUpdateMessage(
            self.bot.account.get_message_by_id(update["msg_id"]),
            update["serial"],
            update["data"],
        )
        replies = Replies(message, logger=logger)
        self.bot.plugins.hook.deltabot_incoming_message(
            message=message, bot=self.bot, replies=replies
        )
        replies.send_reply_messages()

        logger.info(
            "processing status update (msg=%s, serial=%s) FINISHED",
            update["msg_id"],
            update["serial"],
        )

    def process_msg_id(self, msg_id: int) -> None:
        logger = self.bot.logger
        message = self.bot.account.get_message_by_id(msg_id)
        sender = message.get_sender_contact()
        if sender != self.bot.self_contact:
            message.mark_seen()
            encrinfo = from_dc_charpointer(
                lib.dc_get_contact_encrinfo(
                    self.bot.account._dc_context,
                    sender.id,
                )
            )
            can_encrypt = encrinfo.splitlines()[0].lower() != "no encryption."
            can_encrypt = can_encrypt or "Chat-Version" not in (
                message.get_mime_headers() or dict()
            )
        else:
            can_encrypt = True
        if message.is_encrypted() or can_encrypt:
            replies = Replies(message, logger=logger)
            logger.info("processing incoming fresh message id=%s", message.id)
            if message.is_system_message():
                self.handle_system_message(message, replies)
            elif not message.get_sender_contact().is_blocked():
                if message.is_bot():
                    self.bot.plugins.hook.deltabot_incoming_bot_message(
                        message=message, bot=self.bot, replies=replies
                    )
                else:
                    self.bot.plugins.hook.deltabot_incoming_message(
                        message=message, bot=self.bot, replies=replies
                    )
            replies.send_reply_messages()
        else:
            logger.info("ignoring message (id=%s) without autocrypt support", msg_id)
        logger.info("processing message=%s FINISHED", msg_id)

    def handle_system_message(self, message: Message, replies: Replies) -> None:
        logger = self.bot.logger

        res = parse_system_image_changed(message.text)
        if res:
            actor, deleted = res
            logger.debug("calling hook deltabot_image_changed")
            self.bot.plugins.hook.deltabot_image_changed(
                message=message,
                replies=replies,
                chat=message.chat,
                actor=self.bot.account.create_contact(actor),
                deleted=deleted,
                bot=self.bot,
            )
            return

        res = parse_system_title_changed(message.text)
        if res:
            old_title, actor = res
            logger.debug("calling hook deltabot_title_changed")
            self.bot.plugins.hook.deltabot_title_changed(
                message=message,
                replies=replies,
                chat=message.chat,
                actor=self.bot.account.create_contact(actor),
                old=old_title,
                bot=self.bot,
            )
            return

        res = parse_system_add_remove(message.text)
        if res:
            action, affected, actor = res
            hook_name = f"deltabot_member_{action}"
            meth = getattr(self.bot.plugins.hook, hook_name)
            logger.debug("calling hook %s", hook_name)
            meth(
                message=message,
                replies=replies,
                chat=message.chat,
                actor=self.bot.account.create_contact(actor),
                bot=self.bot,
                contact=self.bot.account.create_contact(affected),
            )
            return

        logger.debug("ignoring system message id=%s text: %s", message.id, message.text)


class IncomingEventHandler:
    def __init__(self, bot) -> None:
        self.bot = bot
        self.logger = bot.logger
        self.plugins = bot.plugins
        self._needs_check = threading.Event()
        self._needs_check.set()
        self._running = True
        self._thread: threading.Thread
        self.db: Any

    def start(self) -> None:
        self.logger.debug("starting bot-event-handler THREAD")
        self.db = self.bot.plugins._pm.get_plugin(name="db")
        self.bot.account.add_account_plugin(self)
        self._thread = t = threading.Thread(
            target=self.event_worker, name="bot-event-handler", daemon=True
        )
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
        # accept contact request, just in case "bot" setting is disabled
        message.create_chat()
        self.logger.debug(
            f"incoming message from {message.get_sender_contact().addr} id={message.id} chat={message.chat.id} text={message.text[:50]!r}"
        )

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
        self.logger.debug(
            "message id=%s chat=%s delivered to smtp", message.id, message.chat.id
        )

    @account_hookimpl
    def ac_process_ffi_event(self, ffi_event: FFIEvent) -> None:
        if ffi_event.name == "DC_EVENT_WEBXDC_STATUS_UPDATE":
            msg_id = ffi_event.data1
            serial = ffi_event.data2
            msg = self.bot.account.get_message_by_id(msg_id)
            update = msg.get_status_updates(serial - 1)[0]
            assert update["serial"] == serial

            if isinstance(update["payload"], dict) and "simplebot" in update["payload"]:
                data = update["payload"]["simplebot"]
                text = (data.get("text") or "")[:50]
                self.logger.debug(
                    f"incoming status update, msg={msg_id} serial={serial} text={text!r}"
                )
                self.db.put_msg(
                    json.dumps(dict(msg_id=msg_id, data=data, serial=serial))
                )
                self._needs_check.set()
