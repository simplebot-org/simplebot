from pkg_resources import DistributionNotFound, get_distribution

from .bot import DeltaBot  # noqa
from .commands import command_decorator as command  # noqa
from .filters import filter_decorator as filter  # noqa
from .hookspec import deltabot_hookimpl as hookimpl  # noqa

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    __version__ = "0.0.0.dev0-unknown"
