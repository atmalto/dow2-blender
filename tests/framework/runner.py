"""Test execution engine.

Runs discovered tests against a :class:`TestContext`, routing outcomes into the
:class:`ResultLog`. Returns a process exit code (0 = no failures).
"""

from __future__ import annotations

import traceback
from typing import Callable

from .context import SkipTest, TestContext


def run(ctx: TestContext, tests: list[tuple[str, str, Callable]]) -> int:
    results = ctx.results
    for category, name, func in tests:
        try:
            func(ctx)
        except SkipTest as skip:
            results.add(name, category, "skipped", str(skip))
            print(f"  SKIP  {name}: {skip}")
        except AssertionError as fail:
            detail = str(fail) or "assertion failed"
            results.add(name, category, "failed", detail)
            print(f"  FAIL  {name}: {detail}")
            if not ctx.config.continue_on_error:
                break
        except Exception as exc:  # unexpected error == failure
            detail = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
            results.add(name, category, "failed", detail)
            print(f"  ERROR {name}: {exc}")
            if not ctx.config.continue_on_error:
                break
        else:
            results.add(name, category, "passed")
            print(f"  ok    {name}")

    results.flush()
    print(f"\n[summary] {results.summary_line()}")
    print(f"[logs]    {results.log_dir}")
    return 1 if results.failed else 0
