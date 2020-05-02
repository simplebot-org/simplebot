# -*- coding: utf-8 -*-
import logging
import logging.handlers
import os

import deltachat as dc


_CMD_PREFIX = '/'


class Command():
    def __init__(self, cmd, args, description, action):
        if not cmd.startswith(_CMD_PREFIX):
            raise ValueError('Commands must start with {}'.format(_CMD_PREFIX))
        self.cmd = cmd
        self.args = args
        self.description = description
        self._action = action

    def __call__(self, msg, args):
        return self._action(msg, args)

    def __eq__(self, c):
        return c.cmd == self.cmd


class Filter():
    def __call__(self, msg):
        return False


class DeltaBot:
    def __init__(self, basedir, os_name=None):
        self.commands = []
        self.filters = []

        self.basedir = os.path.abspath(os.path.expanduser(basedir))
        if not os.path.exists(basedir):
            os.makedirs(basedir)

        self._init_logger()
        self.account = _get_account(self.basedir, os_name)
        self.account.set_config('save_mime_headers', '1')
        self.account.set_config('e2ee_enabled', '1')
        self.account.set_config('sentbox_watch', '0')
        self.account.set_config('mvbox_watch', '0')
        self.account.set_config('bcc_self', '0')

    def is_configured(self):
        return bool(self.account.is_configured())

    def configure(self, email, password):
        self.account.configure(addr=email, mail_pw=password)
        self.account.start_threads()
        configured = self._wait_configuration_progress(1000) >= 1000
        self.account.stop_threads()
        if configured:
            self.logger.info('Bot configured successfully!')
        else:
            self.logger.info('Configuration failed')

    def get_blobdir(self):
        return self.account.get_blobdir()

    def set_name(self, name):
        self.account.set_config('displayname', name)

    def send_file(self, chat, path, text, view_type='file'):
        msg = dc.message.Message.new_empty(self.account, view_type)
        msg.set_file(path)
        msg.set_text(text)
        chat.send_msg(msg)

    def add_commands(self, commands):
        self.commands.extend(commands)

    def remove_commands(self, commands):
        for c in commands:
            self.commands.remove(c)

    def add_command(self, cmd):
        self.commands.append(cmd)

    def remove_command(self, cmd):
        self.commands.remove(cmd)

    def add_filters(self, filters):
        self.filters.extend(filters)

    def remove_filters(self, filters):
        for f in filters:
            self.filters.remove(f)

    def add_filter(self, f):
        self.filters.append(f)

    def remove_filter(self, f):
        self.filters.remove(f)

    @staticmethod
    def get_args(cmd, msg):
        """Return the args for the given command or None if the command does not match."""
        if type(msg) is dc.message.Message:
            msg = msg.text
        msg = msg.strip()
        if msg and msg.split()[0] == cmd:
            return msg[len(cmd):].strip()
        return None

    def on_message_delivered(self, msg):
        pass

    def on_self_message(self, msg):
        pass

    def on_message(self, msg):
        processed = False
        for f in self.filters:
            try:
                if f(msg):
                    processed = True
            except Exception as ex:
                self.logger.exception(ex)
        return processed

    def on_command(self, msg):
        for c in self.commands:
            args = self.get_args(c.cmd, msg)
            if args is not None:
                try:
                    c(msg, args)
                    return True
                except Exception as ex:
                    self.logger.exception(ex)
        else:
            return False

    def start(self):
        self.account.start()
        try:
            while True:
                try:
                    ev = self.account._evlogger.get()
                    if ev[0] in ('DC_EVENT_MSGS_CHANGED', 'DC_EVENT_INCOMING_MSG') and ev[2] != 0:
                        msg = self.account.get_message_by_id(int(ev[2]))
                        if msg.get_sender_contact() == self.get_contact():
                            self.on_self_message(msg)
                        else:
                            msg.contact_request = (
                                ev[0] == 'DC_EVENT_MSGS_CHANGED')
                            if msg.text and msg.text.startswith(_CMD_PREFIX):
                                self.on_command(msg)
                            else:
                                self.on_message(msg)
                    elif ev[0] == 'DC_EVENT_MSG_DELIVERED':
                        msg = self.account.get_message_by_id(int(ev[2]))
                        self.on_message_delivered(msg)
                except Exception as ex:
                    self.logger.exception(ex)
        finally:
            self.account.shutdown()

    def get_contact(self, addr=None):
        if addr is None:
            return self.account.get_self_contact()
        else:
            return self.account.create_contact(addr.strip())

    def get_chat(self, ref):
        if type(ref) is dc.message.Message:
            return self.account.create_chat_by_message(ref)
        elif type(ref) is dc.contact.Contact:
            return self.account.create_chat_by_contact(ref)
        elif type(ref) is str and '@' in ref:
            c = self.account.create_contact(ref.strip())
            return self.account.create_chat_by_contact(c)
        elif type(ref) is int:
            try:
                return self.account.get_chat_by_id(ref)
            except ValueError:
                return None

    def get_chats(self):
        return self.account.get_chats()

    def get_address(self):
        return self.get_contact().addr

    def create_group(self, name, members=[]):
        group = self.account.create_group_chat(name)
        for member in members:
            if type(member) is str:
                member = self.account.create_contact(member.strip())
            group.add_contact(member)
        return group

    def is_group(self, chat):
        return chat.get_type() in (dc.const.DC_CHAT_TYPE_GROUP, dc.const.DC_CHAT_TYPE_VERIFIED_GROUP)

    def _wait_configuration_progress(self, target):
        while 1:
            evt_name, data1, data2 = \
                self.account._evlogger.get_matching(
                    "DC_EVENT_CONFIGURE_PROGRESS")
            if data1 >= target or data1 == 0:
                self.logger.info("CONFIG PROGRESS {}".format(data1))
                return data1

    def _init_logger(self):
        logger = logging.Logger('DeltaBot')
        logger.parent = None
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        chandler = logging.StreamHandler()
        chandler.setLevel(logging.DEBUG)
        chandler.setFormatter(formatter)
        logger.addHandler(chandler)

        log_path = os.path.join(self.basedir, 'logs.txt')
        fhandler = logging.handlers.RotatingFileHandler(
            log_path, backupCount=5, maxBytes=2000000)
        fhandler.setLevel(logging.DEBUG)
        fhandler.setFormatter(formatter)
        logger.addHandler(fhandler)

        self.logger = logger


def _get_account(basedir, os_name):
    db_path = os.path.join(basedir, "account.db")
    acc = dc.Account(db_path, os_name=os_name)
    acc.db_path = db_path
    return acc
