"""DoW2 Tools test framework.

A small, dependency-free harness for running the addon's integration and unit
tests headless inside Blender.

Public surface:
    load_config()      -> Config
    ResultLog          -> collects pass/fail/skip and writes per-category logs
    TestContext        -> passed to every test function
    SkipTest, TestFailure
    discover_tests()   -> [(module, callable), ...]
    run(ctx, tests)    -> exit code
"""

from .config import Config, load_config
from .context import SkipTest, TestContext, TestFailure
from .discovery import discover_tests
from .results import ResultLog
from .runner import run

__all__ = [
    "Config",
    "load_config",
    "ResultLog",
    "TestContext",
    "SkipTest",
    "TestFailure",
    "discover_tests",
    "run",
]
