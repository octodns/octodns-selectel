from .v1.provider import SelectelProvider as SelectelProviderLegacy
from .v2.provider import SelectelProvider as SelectelProvider
from .version import __VERSION__, __version__

__all__ = [SelectelProviderLegacy, SelectelProvider]

# quell warnings
__VERSION__
__version__
