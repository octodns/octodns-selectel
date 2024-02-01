from .v1.provider import SelectelProvider as SelectelProviderLegacy
from .v2.provider import SelectelProvider as SelectelProvider

__all__ = [SelectelProviderLegacy, SelectelProvider]
