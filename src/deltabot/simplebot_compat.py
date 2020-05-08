from abc import ABC
from enum import IntEnum
import configparser
import os
import sqlite3
import zipfile
import zlib
import html2text
import pkg_resources
from .bot import DeltaBot, Filter
from . import __version__


html2text.config.WRAP_LINKS = False


class Mode(IntEnum):
    TEXT = 1
    HTML = 2
    HTMLZIP = 3
    TEXT_HTMLZIP = 4
    MD = 5


class Plugin(ABC):
    """Interface for the bot's plugins."""

    name = ''
    description = ''
    long_description = ''
    version = ''
    commands = []
    filters = []

    @classmethod
    def activate(cls, bot):
        """Activate the plugin, this method is called when the bot starts."""
        cls.bot = bot

    @classmethod
    def deactivate(cls):
        """Deactivate the plugin, this method is called before the plugin
        is disabled/removed, do clean up here."""
        cls.bot.remove_commands(cls.commands)
        cls.bot.remove_filters(cls.filters)


class PluginFilter(Filter):
    def __init__(self, action):
        self._action = action

    def __call__(self, ctx):
        self._action(ctx)


class Context:
    rejected = False
    processed = False

    def __init__(self, msg, text=None, locale='en', mode=Mode.HTML):
        self.msg = msg
        self.text = msg.text if text is None else text
        self.locale = locale
        self.mode = mode


class DBManager:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.execute('''CREATE TABLE IF NOT EXISTS preferences
                        (addr TEXT PRIMARY KEY,
                         locale TEXT,
                         mode INTEGER)''')
        self.execute('''CREATE TABLE IF NOT EXISTS config
                        (keyname TEXT PRIMARY KEY,
                         value TEXT)''')

    def execute(self, statement, args=()):
        with self.db:
            return self.db.execute(statement, args)

    def close(self):
        self.db.close()


class SimpleBot(DeltaBot):
    # deltachat.account.Account instance
    account = None
    # the list of installed plugins
    plugins = None
    # logging.Logger compatible instance
    logger = None
    # locale to start the bot: es, en, etc.
    locale = 'en'
    # base directory for the bot configuration and db file
    basedir = None

    def __init__(self, basedir):
        super().__init__(basedir, 'SimpleBot {}'.format(__version__))

        self._db = DBManager(os.path.join(self.basedir, 'simplebot.db'))
        self._cfg = configparser.ConfigParser(allow_no_value=True)
        self._cfg.path = os.path.join(self.basedir, 'simplebot.cfg')
        self._load_config()

        self._mdl = set()
        self._mpl = set()
        self._cdl = set()
        self._cpl = set()

        self.register_command(
            name="/settings", args=['<property>', '<value>'],
            description="Set key value setting",
            func=self._settings_cmd
        )
        self.register_command(
            name="/start", args=[],
            description="Show an information message",
            func=self._start_cmd
        )
        self.plugins = []   # self.load_plugins()
        self.load_plugins()

    def start(self):
        self.activate_plugins()
        try:
            super().start()
        finally:
            self.deactivate_plugins()

    def send_html(self, chat, html, basename, text, mode):
        if mode in (Mode.HTMLZIP, Mode.TEXT_HTMLZIP):
            file_path = self.get_blobpath(basename + '.html.zip')
            zlib.Z_DEFAULT_COMPRESSION = 9
            with zipfile.ZipFile(file_path, 'w', compression=zipfile.ZIP_DEFLATED) as fd:
                fd.writestr('index.html', html)
            self.send_file(chat, file_path, text)
        else:
            if mode == Mode.MD:
                file_path = self.get_blobpath(basename + '.md')
                html = html2text.html2text(html)
            else:
                file_path = self.get_blobpath(basename + '.html')
            with open(file_path, 'w') as fd:
                fd.write(html)
            self.send_file(chat, file_path, text)
        return file_path

    def get_blobpath(self, basename):
        path = os.path.join(self.get_blobdir(), basename)

        basename = basename.split('.', 1)
        if len(basename) == 2:
            basename, extension = basename[0], '.' + basename[1]
        else:
            basename, extension = basename[0], ''

        i = 1
        while os.path.exists(path):
            path = os.path.join(self.get_blobdir(),
                                '{}-{}{}'.format(basename, i, extension))
            i += 1

        return path

    def get_dir(self, plugin_name):
        pdir = os.path.join(self.basedir, plugin_name)
        if not os.path.exists(pdir):
            os.makedirs(pdir)
        return pdir

    def _load_config(self):
        if os.path.exists(self._cfg.path):
            self._cfg.read(self._cfg.path)

        botcfg = self.get_config(__name__)
        botcfg.setdefault(
            'start_msg', 'This is deltabot, a bot '
            'for the Delta Chat application.\n\n'
            'Source code: https://github.com/deltachat-bot/deltabot'
        )
        botcfg.setdefault('displayname', '🤖deltabot🤖')
        botcfg.setdefault('avatar', '1')
        botcfg.setdefault('mdns_enabled', '0')
        botcfg.setdefault('mvbox_move', '0')
        botcfg.setdefault('e2ee_enabled', '1')
        self.save_config()

        self.set_name(botcfg['displayname'])

        # set avatar if it isn't the current avatar
        row = self._db.execute(
            'SELECT * FROM config WHERE keyname="avatar"').fetchone()
        if not row:
            self._db.execute(
                'INSERT INTO config VALUES ("avatar",?)', (botcfg['avatar'],))
            row = {'keyname': 'avatar', 'value': None}
        if row['value'] != botcfg['avatar']:
            self._db.execute(
                'UPDATE config SET value=? WHERE keyname="avatar"', (botcfg['avatar'],))
            if botcfg['avatar']:
                if botcfg['avatar'].isdigit():
                    avatar = os.path.join(os.path.dirname(
                        __file__), 'assets', 'avatar{}.png'.format(botcfg['avatar']))
                    self.account.set_avatar(avatar)
                else:
                    self.account.set_avatar(botcfg['avatar'])

        self.account.set_config('mdns_enabled', botcfg['mdns_enabled'])
        self.account.set_config('mvbox_move', botcfg['mvbox_move'])
        self.account.set_config('e2ee_enabled', botcfg['e2ee_enabled'])

    def _start_cmd(self, command):
        botcfg = self.get_config(__name__)
        command.message.chat.send_text(botcfg['start_msg'])

    def _settings_cmd(self, command):
        """Set your preferences, "property" can be "locale"(values: en, es, de, etc)
        or "mode"(values: text, md, html, html.zip, text/html.zip)"""
        prop, value = command.args.split(maxsplit=1)
        prop = prop.lower()
        value = value.rstrip()
        addr = command.msg.get_sender_contact().addr
        if prop == 'locale':
            row = self._db.execute(
                'SELECT locale FROM preferences WHERE addr=?', (addr,)).fetchone()
            if row:
                if row[0] != value:
                    self._db.execute(
                        'UPDATE preferences SET locale=? WHERE addr=?', (value, addr))
            else:
                self._db.execute(
                    'INSERT INTO preferences VALUES (?,?,?)', (addr, value, None))
        elif prop == 'mode':
            if value == 'text':
                mode = Mode.TEXT
            elif value == 'html':
                mode = Mode.HTML
            elif value == 'html.zip':
                mode = Mode.HTMLZIP
            elif value == 'text/html.zip':
                mode = Mode.TEXT_HTMLZIP
            elif value == 'md':
                mode = Mode.MD
            else:
                command.msg.send_text(
                    'Invalid value: {!r}'.format(value))
                return
            row = self._db.execute(
                'SELECT mode FROM preferences WHERE addr=?', (addr,)).fetchone()
            if row:
                if row[0] != mode:
                    self._db.execute(
                        'UPDATE preferences SET mode=? WHERE addr=?', (mode, addr))
            else:
                self._db.execute(
                    'INSERT INTO preferences VALUES (?,?,?)', (addr, None, mode))
        else:
            command.msg.chat.send_text(
                'Unknown property: {!r}'.format(prop))

    def get_config(self, section):
        if not self._cfg.has_section(section):
            self._cfg.add_section(section)
        return self._cfg[section]

    def save_config(self):
        with open(self._cfg.path, 'w') as fd:
            self._cfg.write(fd)

    def add_on_msg_detected_listener(self, listener):
        self._mdl.add(listener)

    def add_on_msg_processed_listener(self, listener):
        self._mpl.add(listener)

    def remove_on_msg_detected_listener(self, listener):
        self._mdl.discard(listener)

    def remove_on_msg_processed_listener(self, listener):
        self._mpl.discard(listener)

    def add_on_cmd_detected_listener(self, listener):
        self._cdl.add(listener)

    def add_on_cmd_processed_listener(self, listener):
        self._cpl.add(listener)

    def remove_on_cmd_detected_listener(self, listener):
        self._cdl.discard(listener)

    def remove_on_cmd_processed_listener(self, listener):
        self._cpl.discard(listener)

    # def on_message_delivered(self, msg):
    #     self.account.delete_messages((msg,))

    def on_message(self, msg):
        if type(msg) is Context:
            ctx = msg
            addr = ctx.msg.get_sender_contact().addr
        else:
            addr = msg.get_sender_contact().addr
            ctx = Context(msg)
            prefs = self.get_preferences(addr)
            ctx.locale = prefs['locale']
            ctx.mode = prefs['mode']

        self.logger.debug('Received message from {}'.format(addr,))

        headers = ctx.msg.get_mime_headers()
        if headers['chat-version'] is None or 'SimpleBot' in headers.get('X-Mailer', ''):
            self.logger.debug('Email rejected')
            self.account.delete_messages((ctx.msg,))
            return

        for listener in self._mdl:
            try:
                listener(ctx)
                if ctx.rejected:
                    self.logger.debug('Message rejected')
                    self.account.delete_messages((ctx.msg,))
                    return
            except Exception as ex:
                self.logger.exception(ex)

        for f in self.filters:
            try:
                f(ctx)
                if ctx.processed:
                    self.logger.debug('Message processed')
            except Exception as ex:
                self.logger.exception(ex)

        if not ctx.processed:
            self.logger.debug('Message was not processed')

        for listener in self._mpl:
            try:
                listener(ctx)
            except Exception as ex:
                self.logger.exception(ex)

        self.account.mark_seen_messages([ctx.msg])

    def on_command(self, msg):
        if type(msg) is Context:
            ctx = msg
            addr = ctx.msg.get_sender_contact().addr
        else:
            addr = msg.get_sender_contact().addr
            ctx = Context(msg)
            prefs = self.get_preferences(addr)
            ctx.locale = prefs['locale']
            ctx.mode = prefs['mode']

        self.logger.debug('Received command from {}'.format(addr,))

        headers = ctx.msg.get_mime_headers()
        if headers['chat-version'] is None or 'SimpleBot' in headers.get('X-Mailer', ''):
            self.logger.debug('Email rejected')
            self.account.delete_messages((ctx.msg,))
            return

        for listener in self._cdl:
            try:
                listener(ctx)
                if ctx.rejected:
                    self.logger.debug('Command rejected')
                    self.account.delete_messages((ctx.msg,))
                    return
            except Exception as ex:
                self.logger.exception(ex)

        for c in self.commands:
            args = self.get_args(c.cmd, ctx.text)
            if args is not None:
                ctx.text = args
                try:
                    c(ctx)
                    ctx.processed = True
                    self.logger.debug('Command processed: {}'.format(c.cmd))
                    break
                except Exception as ex:
                    self.logger.exception(ex)

        if not ctx.processed:
            self.logger.debug('Command was not processed')

        for listener in self._cpl:
            try:
                listener(ctx)
            except Exception as ex:
                self.logger.exception(ex)

        self.account.mark_seen_messages([ctx.msg])

    def get_preferences(self, addr):
        prefs = {'locale': self.locale, 'mode': Mode.HTML}
        row = self._db.execute(
            'SELECT locale, mode FROM preferences WHERE addr=?', (addr,)).fetchone()
        if row:
            if row[0] is not None:
                prefs['locale'] = row[0]
            if row[1] is not None:
                prefs['mode'] = row[1]
        return prefs

    def load_plugins(self):
        self.plugins = []
        plugins = self.get_config("simplebot").get('plugins', '').split()
        for ep in pkg_resources.iter_entry_points('simplebot.plugins'):
            if plugins and ep.module_name not in plugins:
                continue
            try:
                self.plugins.append(ep.load())
            except Exception as ex:
                self.logger.exception(ex)

    def activate_plugins(self):
        for plugin in self.plugins:
            plugin.activate(self)

    def deactivate_plugins(self):
        for plugin in self.plugins:
            try:
                plugin.deactivate()
            except Exception as ex:
                self.logger.exception(ex)
