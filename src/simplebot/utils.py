import configparser
import logging
import os
import re
from tempfile import NamedTemporaryFile
from threading import Event
from typing import List, Optional, Tuple
from urllib.parse import quote, unquote

import deltachat
from deltachat import hookspec
from deltachat.account import Account
from deltachat.capi import ffi, lib
from deltachat.cutil import as_dc_charpointer, from_optional_dc_charpointer
from deltachat.events import EventThread, FFIEvent
from deltachat.message import extract_addr
from PIL import Image
from PIL.ImageColor import getcolor, getrgb
from PIL.ImageOps import grayscale

# disable Pillow debugging to stdout
logging.getLogger("PIL").setLevel(logging.ERROR)


def set_builtin_avatar(bot, name: str = "adaptive-default") -> bool:
    ext = ".png"
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "avatars", name + ext
    )
    if not os.path.exists(path):
        return False

    if name.startswith("adaptive-"):
        color = "#" + hex(bot.get_chat(bot.self_contact).get_color())[2:].zfill(6)
        blobdir = bot.account.get_blobdir()
        with NamedTemporaryFile(
            dir=blobdir, prefix="avatar-", suffix=ext, delete=False
        ) as fp:
            result_path = fp.name
        image_tint(path, color).save(result_path)
        path = result_path

    bot.account.set_avatar(path)
    return True


def get_builtin_avatars() -> list:
    avatars = os.listdir(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "avatars")
    )
    return [os.path.splitext(name)[0] for name in avatars]


def get_config_folder() -> str:
    return os.path.join(os.path.expanduser("~"), ".simplebot")


def get_account_path(address: str) -> str:
    return os.path.join(get_config_folder(), "accounts", quote(address))


def get_accounts() -> List[Tuple[str, str]]:
    accounts_dir = os.path.join(get_config_folder(), "accounts")
    accounts = []
    if os.path.exists(accounts_dir):
        folders = os.listdir(accounts_dir)
    else:
        folders = []
    for folder in folders:
        accounts.append((unquote(folder), os.path.join(accounts_dir, folder)))
    return accounts


def set_default_account(addr: str) -> None:
    config = configparser.ConfigParser()
    config["DEFAULT"]["default_account"] = addr
    path = os.path.join(get_config_folder(), "global.cfg")
    with open(path, "w", encoding="utf-8") as configfile:
        config.write(configfile)


def get_default_account() -> str:
    config = configparser.ConfigParser()
    path = os.path.join(get_config_folder(), "global.cfg")
    if os.path.exists(path):
        config.read(path)
    def_account = config["DEFAULT"].get("default_account")
    if not def_account:
        accounts = get_accounts()
        if len(accounts) == 1:
            def_account = accounts[0][1]
    return def_account


def image_tint(path: str, tint: str) -> Image:
    src = Image.open(path)
    if src.mode not in ("RGB", "RGBA"):
        raise TypeError(f"Unsupported source image mode: {src.mode}")
    src.load()

    tr, tg, tb = getrgb(tint)
    tl = getcolor(tint, "L")  # tint color's overall luminosity
    if not tl:
        tl = 1  # avoid division by zero
    tl = float(tl)  # compute luminosity preserving tint factors
    sr, sg, sb = map(lambda tv: tv / tl, (tr, tg, tb))  # per component
    # adjustments
    # create look-up tables to map luminosity to adjusted tint
    # (using floating-point math only to compute table)
    luts = (
        tuple(map(lambda lr: int(lr * sr + 0.5), range(256)))
        + tuple(map(lambda lg: int(lg * sg + 0.5), range(256)))
        + tuple(map(lambda lb: int(lb * sb + 0.5), range(256)))
    )
    l = grayscale(src)  # 8-bit luminosity version of whole image
    if Image.getmodebands(src.mode) < 4:
        merge_args: tuple = (src.mode, (l, l, l))  # for RGB verion of grayscale
    else:  # include copy of src image's alpha layer
        a = Image.new("L", src.size)
        a.putdata(src.getdata(3))
        merge_args = (src.mode, (l, l, l, a))  # for RGBA verion of grayscale
        luts += tuple(range(256))  # for 1:1 mapping of copied alpha values

    image = Image.merge(*merge_args).point(luts)
    new_image = Image.new("RGBA", image.size, "WHITE")  # Create a white rgba background
    new_image.paste(image, (0, 0), image)
    return new_image


def parse_system_title_changed(text: str, title: str) -> Optional[tuple]:
    text = text.lower()
    regex = fr'group name changed from "(.+)" to "{re.escape(title)}" by (.+).'
    m = re.match(regex, text)
    if m:
        old_title, actor = m.groups()
        return (old_title, extract_addr(actor))
    return None


def parse_system_image_changed(text: str) -> Optional[tuple]:
    text = text.lower()
    m = re.match(r"group image (changed|deleted) by (.+).", text)
    if m:
        action, actor = m.groups()
        return (extract_addr(actor), action == "deleted")
    return None


class BotEventThread(EventThread):
    """Class patching deltachat.events.EventThread."""

    def __init__(self, account: Account, logger: logging.Logger) -> None:
        self.logger = logger
        super().__init__(account)

    def _inner_run(self) -> None:
        event_emitter = ffi.gc(
            lib.dc_get_event_emitter(self.account._dc_context),
            lib.dc_event_emitter_unref,
        )
        while not self._marked_for_shutdown:
            event = lib.dc_get_next_event(event_emitter)
            if event == ffi.NULL:
                break
            if self._marked_for_shutdown:
                break
            evt = lib.dc_event_get_id(event)
            data1 = lib.dc_event_get_data1_int(event)
            # the following code relates to the deltachat/_build.py's helper
            # function which provides us signature info of an event call
            evt_name = deltachat.get_dc_event_name(evt)
            if lib.dc_event_has_string_data(evt):
                data2 = from_optional_dc_charpointer(lib.dc_event_get_data2_str(event))
            else:
                data2 = lib.dc_event_get_data2_int(event)

            lib.dc_event_unref(event)
            ffi_event = FFIEvent(name=evt_name, data1=data1, data2=data2)
            try:
                self.account._pm.hook.ac_process_ffi_event(
                    account=self, ffi_event=ffi_event
                )
                for name, kwargs in self._map_ffi_event(ffi_event):
                    self.account.log(f"calling hook name={name} kwargs={kwargs}")
                    hook = getattr(self.account._pm.hook, name)
                    hook(**kwargs)
            except Exception as err:
                if self.account._dc_context is not None:
                    self.logger.exception(err)


class BotAccount(Account):
    """Class patching deltachat.account.Account."""

    def __init__(  # noqa
        self, db_path: str, os_name: str, logger: logging.Logger
    ) -> None:
        """initialize account object.

        :param db_path: a path to the account database. The database
                        will be created if it doesn't exist.
        :param os_name: this is only for decorative use.
        :param logger: account logger.
        """
        # initialize per-account plugin system
        self._pm = hookspec.PerAccount._make_plugin_manager()
        self._logging = True

        self.add_account_plugin(self)

        self.db_path = db_path
        if hasattr(db_path, "encode"):
            db_path = db_path.encode("utf8")  # type: ignore

        self._dc_context = ffi.gc(
            lib.dc_context_new(as_dc_charpointer(os_name), db_path, ffi.NULL),
            lib.dc_context_unref,
        )
        if self._dc_context == ffi.NULL:
            raise ValueError(f"Could not dc_context_new: {os_name} {db_path}")

        self._shutdown_event = Event()
        self._event_thread = BotEventThread(self, logger)
        self._configkeys = self.get_config("sys.config_keys").split()
        hook = hookspec.Global._get_plugin_manager().hook
        hook.dc_account_init(account=self)
