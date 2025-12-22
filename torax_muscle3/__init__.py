from pathlib import Path

try:
    from ._version import version as __version__
except ImportError:
    __version__ = "unknown"

version = __version__


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent
