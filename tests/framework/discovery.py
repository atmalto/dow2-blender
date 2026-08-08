"""Test discovery.

Walks the ``suites`` package and collects every ``test_*`` callable. Each suite
module may define a module-level ``CATEGORY`` string used for log bucketing;
it defaults to the module's dotted name under ``suites``.
"""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType
from typing import Callable


def _iter_suite_modules() -> list[ModuleType]:
    import suites  # available once tests/ is on sys.path

    modules: list[ModuleType] = []
    for info in pkgutil.walk_packages(suites.__path__, prefix="suites."):
        if info.ispkg:
            continue
        modules.append(importlib.import_module(info.name))
    return modules


def discover_tests() -> list[tuple[str, str, Callable]]:
    """Return ``(category, test_name, func)`` tuples for all discovered tests."""
    discovered: list[tuple[str, str, Callable]] = []
    for module in _iter_suite_modules():
        category = getattr(module, "CATEGORY", module.__name__.replace("suites.", ""))
        for attr in sorted(dir(module)):
            if not attr.startswith("test_"):
                continue
            func = getattr(module, attr)
            if callable(func):
                discovered.append((category, f"{module.__name__}.{attr}", func))
    return discovered
