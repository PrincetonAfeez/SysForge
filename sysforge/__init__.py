"""SysForge: a developer operations toolkit."""

__all__ = ["__version__"]

__version__ = "0.2.0"

from ._import_shims import install_markdown_alias_finder

install_markdown_alias_finder()
