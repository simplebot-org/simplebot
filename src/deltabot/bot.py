# -*- coding: utf-8 -*-

import threading
from queue import Queue

import deltachat as dc
from deltachat import account_hookimpl
from deltachat import Message, Contact
from deltachat.tracker import ConfigureTracker

from .commands import Commands
from .filters import Filters
from .plugins import Plugins, get_global_plugin_manager


class DeltaBot:
    def __init__(self, account, logger, plugin_manager=None):

        # by default we will use the global instance of the
        # plugin_manager.
        if plugin_manager is None:
            plugin_manager = get_global_plugin_manager()

        self.account = account

        self.logger = logger

        #: plugin subsystem for adding/removing plugins and calling plugin hooks
        self.plugins = Plugins(logger=logger, plugin_manager=plugin_manager)

        #: commands subsystem for registering/executing '/*' commands in incoming messages
        self.commands = Commands(self)

        #: filter subsystem for registering/performing filters on incoming messages
        self.filters = Filters(self)

        # process dc events and turn them into deltabot ones
        self._eventhandler = IncomingEventHandler(self)

        # set some useful bot defaults on the account
        self.account.update_config(dict(
            save_mime_headers=1,
            e2ee_enabled=1,
            sentbox_watch=0,
            mvbox_watch=0,
            bcc_self=0
        ))

    #
    # API for persistent scoped-key/value settings
    #
    def set(self, name, value, scope="global"):
        """ Store a per bot setting with the given scope. """
        assert "/" not in scope and "/" not in name
        key = scope + "/" + name
        self.plugins._pm.hook.deltabot_store_setting(key=key, value=value)

    def get(self, name, default=None, scope="global"):
        """ Get a per-bot setting from the given scope. """
        assert "/" not in scope and "/" not in name
        key = scope + "/" + name
        res = self.plugins._pm.hook.deltabot_get_setting(key=key)
        return res if res is not None else default

    def list_settings(self, scope=None):
        """ list per-bot settings for the given scope.

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
    def self_contact(self):
        """ this bot's contact (with .addr and .display_name attributes). """
        return self.account.get_self_contact()

    def get_contact(self, ref):
        """ return Contact object (create one if needed) for the specified 'ref'.

        ref can be a Contact, email address string or contact id.
        """
        if isinstance(ref, str):
            return self.account.create_contact(ref)
        elif isinstance(ref, int):
            return self.account.get_contact_by_id(ref)
        elif isinstance(ref, Contact):
            return ref

    def get_chat(self, ref):
        """ Return a 1:1 chat (creating one if needed) from the specified ref object.

        ref can be a Message, Contact, email address string or chat-id integer.
        """
        if isinstance(ref, dc.message.Message):
            return self.account.create_chat_by_message(ref)
        elif isinstance(ref, dc.contact.Contact):
            return self.account.create_chat_by_contact(ref)
        elif isinstance(ref, str) and '@' in ref:
            return self.account.create_contact(ref).get_chat()
        elif type(ref) is int:
            try:
                return self.account.get_chat_by_id(ref)
            except ValueError:
                return None

    def create_group(self, name, members=[]):
        """ Create a new group chat. """
        group = self.account.create_group_chat(name)
        for member in map(self.get_contact, members):
            group.add_contact(member)
        return group

    #
    # configuration related API
    #

    def is_configured(self):
        """ Return True if this bot account is successfully configured. """
        return bool(self.account.is_configured())

    def perform_configure_address(self, email, password):
        """ perform initial email/password bot account configuration.  """
        # XXX support reconfiguration (changed password at least)
        assert not self.is_configured()
        assert not self.account._threads.is_started()
        with self.account.temp_plugin(ConfigureTracker()) as configtracker:
            self.account.update_config(dict(addr=email, mail_pw=password))
            self.account.start()
            try:
                configtracker.wait_finish()
            except configtracker.ConfigureFailed as ex:
                success = False
                self.logger.error('Failed to configure: {}'.format(ex))
            else:
                success = True
                self.logger.info('Successfully configured {}'.format(email))
            self.account.shutdown()
            return success

    #
    # start/wait/shutdown API
    #
    def start(self):
        """ Start bot threads and processing messages. """
        addr = self.account.get_config("addr")
        self.logger.info("bot connected at: {}".format(addr))
        self._eventhandler.start()
        if not self.account._threads.is_started():
            self.account.start()

    def wait_shutdown(self):
        """ Wait and block until bot account is shutdown. """
        self.account.wait_shutdown()
        self._eventhandler.stop()

    def trigger_shutdown(self):
        """ Trigger a shutdown of the bot. """
        self._eventhandler.stop()
        self.plugins.hook.deltabot_shutdown(bot=self)
        self.account.shutdown()


class CheckAll:
    def __init__(self, bot):
        self.bot = bot

    def perform(self):
        logger = self.bot.logger
        for message in self.bot.account.get_fresh_messages():
            try:
                replies = Replies(message.account)
                logger.info("processing incoming fresh message id={}".format(message.id))
                self.bot.plugins.hook.deltabot_incoming_message(
                    message=message,
                    bot=self.bot,
                    replies=replies
                )
                for msg in replies.get_reply_messages():
                    msg = message.chat.send_msg(msg)
                    logger.info("reply id={} chat={} sent with text: {!r}".format(
                        msg.id, msg.chat, msg.text[:50]
                    ))
            except Exception as ex:
                logger.exception("processing message={} failed: {}".format(
                    message.id, ex))
            logger.info("processing message id={} FINISHED".format(message.id))
            message.mark_seen()


class IncomingEventHandler:
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.plugins = bot.plugins
        self.bot.account.add_account_plugin(self)
        self._checks = Queue()
        self._checks.put(CheckAll(bot))

    def start(self):
        self._thread = t = threading.Thread(target=self.event_worker, name="bot-event-handler")
        t.setDaemon(1)
        t.start()

    def stop(self):
        self._checks.put(None)

    def event_worker(self):
        self.logger.debug("event-worker startup")
        while 1:
            check = self._checks.get()
            if check is None:
                break
            check.perform()

    @account_hookimpl
    def ac_incoming_message(self, message):
        # we always accept incoming messages to remove the need  for
        # bot authors to having to deal with deaddrop/contact requests.
        message.accept_sender_contact()
        self.logger.info("incoming message from {} id={} chat={} text={!r}".format(
            message.get_sender_contact().addr,
            message.id, message.chat.id, message.text[:50]))

        # message is now in fresh state, schedule a check
        self._checks.put(CheckAll(self.bot))

    @account_hookimpl
    def ac_message_delivered(self, message):
        self.logger.info("message id={} chat={} delivered to smtp".format(
            message.id, message.chat.id))


class Replies:
    def __init__(self, account):
        self.account = account
        self._replies = []

    def add(self, text=None, filename=None):
        """ Add a text or file-based reply. """
        self._replies.append((text, filename))

    def get_reply_messages(self):
        for text, file in self._replies:
            if file:
                view_type = "file"
            else:
                view_type = "text"
            msg = Message.new_empty(self.account, view_type)
            if text is not None:
                msg.set_text(text)
            if file is not None:
                msg.set_file(file)
            yield msg
