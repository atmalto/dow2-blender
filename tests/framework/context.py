"""Test context and control-flow exceptions passed to every test function."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Config
    from .results import ResultLog


class SkipTest(Exception):
    """Raised to skip a test (e.g. required game data is missing)."""


class TestFailure(AssertionError):
    """Raised to fail a test with a message (AssertionError also counts as failure)."""


class TestContext:
    """Everything a test function needs.

    Passed as the single argument to each ``test_*(ctx)`` function.
    """

    def __init__(self, config: "Config", results: "ResultLog") -> None:
        self.config = config
        self.results = results

    # -- control flow -----------------------------------------------------
    def skip(self, reason: str) -> "None":
        raise SkipTest(reason)

    def fail(self, message: str) -> "None":
        raise TestFailure(message)

    # -- guards -----------------------------------------------------------
    def require_data(self) -> None:
        """Skip the current test if the DoW2 Data root is unavailable."""
        if not self.config.data_root_available:
            self.skip(f"DATA_ROOT unavailable: {self.config.data_root}")

    def data_path(self, *parts: str) -> Path:
        """Path inside DATA_ROOT; skips the test if the asset is missing."""
        self.require_data()
        p = self.config.data_root.joinpath(*parts)
        if not p.exists():
            self.skip(f"asset missing: {p}")
        return p
