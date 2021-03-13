
import os


def get_builtin_avatar(name: str) -> str:
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'avatars', name + '.png')


def get_builtin_avatars() -> list:
    avatars = os.listdir(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'avatars'))
    return [name.split('.')[0] for name in avatars]
