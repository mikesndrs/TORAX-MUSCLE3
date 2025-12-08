from pathlib import Path

from . import _version

__version__ = _version.get_versions()["version"]

version = __version__


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent
