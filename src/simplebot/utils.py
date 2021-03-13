import configparser
import os
from urllib.parse import quote, unquote


def get_builtin_avatar(name: str) -> str:
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'avatars', name + '.png')


def get_builtin_avatars() -> list:
    avatars = os.listdir(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'avatars'))
    return [name.split('.')[0] for name in avatars]


def get_config_folder() -> str:
    return os.path.join(os.path.expanduser('~'), '.config', 'simplebot')


def get_account_path(address: str) -> str:
    return os.path.join(get_config_folder(), 'accounts', quote(address))


def get_accounts() -> list:
    accounts_dir = os.path.join(get_config_folder(), 'accounts')
    accounts = []
    for folder in os.listdir(accounts_dir):
        accounts.append((unquote(folder), os.path.join(accounts_dir, folder)))
    return accounts


def set_default_account(addr: str) -> None:
    config = configparser.ConfigParser()
    config['DEFAULT']['default_account'] = addr
    path = os.path.join(get_config_folder(), 'global.cfg')
    with open(path, 'w') as configfile:
        config.write(configfile)


def get_default_account() -> str:
    config = configparser.ConfigParser()
    path = os.path.join(get_config_folder(), 'global.cfg')
    if os.path.exists(path):
        config.read(path)
    return config['DEFAULT'].get('default_account')
