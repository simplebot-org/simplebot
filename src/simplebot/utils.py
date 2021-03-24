import configparser
import logging
import os
import re
from tempfile import NamedTemporaryFile
from typing import Optional
from urllib.parse import quote, unquote

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
        with NamedTemporaryFile(dir=blobdir, suffix=ext, delete=False) as fp:
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
    return os.path.join(os.path.expanduser("~"), ".config", "simplebot")


def get_account_path(address: str) -> str:
    return os.path.join(get_config_folder(), "accounts", quote(address))


def get_accounts() -> list:
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
    with open(path, "w") as configfile:
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
            def_account = accounts[0]
    return def_account


def image_tint(path: str, tint: str) -> Image:
    src = Image.open(path)
    if src.mode not in ("RGB", "RGBA"):
        raise TypeError("Unsupported source image mode: {}".format(src.mode))
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
    regex = r'group name changed from "(.+)" to "{}" by (.+).'.format(re.escape(title))
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
