from __future__ import annotations

import importlib.util
import sys
import types
import warnings
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec



class _SysforgeMarkdownAliasFinder(MetaPathFinder):

    _warned = False

    @classmethod
    def _emit_deprecation(cls) -> None:
        if cls._warned:
            return
        cls._warned = True
        warnings.warn(
            "Importing sysforge.markdown is deprecated and will be removed in a future "
            "release; use sysforge.mdhtml instead.",
            DeprecationWarning,
            stacklevel=2,
        )

    @classmethod
    def find_spec(
        cls,
        fullname: str,
        path: object | None = None,
        target: types.ModuleType | None = None,
    ) -> ModuleSpec | None:
        if fullname == "sysforge.markdown":
            return importlib.util.spec_from_loader(
                fullname, _MarkdownPackageLoader(), is_package=True
            )
        if fullname == "sysforge.markdown.markdown":
            return importlib.util.spec_from_loader(
                fullname, _MarkdownModuleLoader(), is_package=False
            )
        return None

