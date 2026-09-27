"""Pamfilico Python utility functions and helpers."""

from importlib.metadata import PackageNotFoundError, version as _dist_version

try:
    #: Read from the INSTALLED distribution, never hardcoded — a literal here is
    #: one more thing that can drift from pyproject.toml and from the git tag,
    #: which is the exact failure this is meant to make visible. Consumers pin by
    #: tag and can assert on this to prove which build they actually got.
    __version__ = _dist_version("pamfilico-python-utils")
except PackageNotFoundError:  # running from a source tree, not installed
    __version__ = "0.0.0.dev0"

from pamfilico_python_utils.sqlalchemy import (
    DateTimeMixin,
    NextAuthAccountMixin,
    NextAuthSessionMixin,
    NextAuthUserMixin,
    NextAuthVerificationTokenMixin,
    generate_uuid,
)
from pamfilico_python_utils.storage import DigitalOceanSpacesClient

__all__ = [
    "__version__",
    "DateTimeMixin",
    "NextAuthAccountMixin",
    "NextAuthSessionMixin",
    "NextAuthUserMixin",
    "NextAuthVerificationTokenMixin",
    "generate_uuid",
    "DigitalOceanSpacesClient",
]
