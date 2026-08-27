"""
Resolution of approved locations (spec section 13).

The ALLOWED_DIRECTORIES settings define the only folders Astra may
touch.  Everything else is refused at the capability and tool
layers.
"""

from config.settings import ALLOWED_DIRECTORIES


def resolve(name, path=None):
    """Absolute path for a canonical location name, or None."""

    if path:
        return path

    if name in ALLOWED_DIRECTORIES:
        return ALLOWED_DIRECTORIES[name]

    return None


def all_directories():
    """Every approved directory, name -> path."""

    return dict(ALLOWED_DIRECTORIES)