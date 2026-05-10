"""Local mock server for social media platform APIs."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("postpit")
except PackageNotFoundError:
    __version__ = "0.0.0"
