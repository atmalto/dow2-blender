"""DoW2 Tools test suite entry point 
- Runs on blender 4.3
- Single command that works from either context:
    # usign normal shell (auto-relaunches inside Blender headless):
    python tests/run.py
    # directly inside Blender:
    blender --background --python tests/run.py

"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent


def _script_args() -> list[str]:
    """Return the arguments meant for this script in either launch context."""
    argv = sys.argv
    if "--" in argv:  # inside Blender: script args follow a lone "--"
        return argv[argv.index("--") + 1:]
    return argv[1:]  # plain-python launch


def _parse_args(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="tests/run.py", description="DoW2 Tools test runner")
    parser.add_argument(
        "--scope",
        choices=["small", "medium", "large"],
        default=None,
        help="Asset scope preset (overrides [scope].default in config).",
    )
    parser.add_argument(
        "--build-test-data",
        action="store_true",
        help="Run the Phase-A generator (build tests/test_data from seed models) instead of the suite.",
    )
    return parser.parse_args(args)


def _running_in_blender() -> bool:
    try:
        import bpy  # noqa: F401  # type: ignore
        return True
    except ModuleNotFoundError:
        return False


def _relaunch_in_blender(args: list[str]) -> int:
    """Re-run this script inside Blender headless using the configured path."""
    import subprocess

    sys.path.insert(0, str(TESTS_ROOT))
    from framework.config import load_config

    config = load_config()
    blender_exe = config.blender_exe
    if not blender_exe.is_file():
        print(f"ERROR: blender.exe not found at {blender_exe} (check config).", file=sys.stderr)
        return 2

    cmd = [str(blender_exe), "--background", "--python", str(Path(__file__).resolve()), "--", *args]
    print(f"[run] relaunching inside Blender: {blender_exe}")
    return subprocess.call(cmd)


def _run_inside_blender(ns: argparse.Namespace) -> int:
    sys.path.insert(0, str(TESTS_ROOT))

    from framework import ResultLog, TestContext, discover_tests, load_config, run
    from framework.blender_env import ensure_addon_enabled

    config = load_config(scope=ns.scope)
    ensure_addon_enabled()

    if ns.build_test_data:
        from framework.test_data_builder import build_seed_test_data

        return build_seed_test_data(config)

    results = ResultLog(log_dir=config.log_dir)
    ctx = TestContext(config, results)

    tests = discover_tests()
    print(f"[run] config: {config.source}")
    print(
        f"[run] scope: {config.scope} "
        f"(models<= {config.model_limit}, anims<= {config.animation_limit}, physics<= {config.physics_limit})"
    )
    print(f"[run] data_root available: {config.data_root_available}")
    print(f"[run] discovered {len(tests)} test(s)\n")

    return run(ctx, tests)


def main() -> int:
    args = _script_args()
    ns = _parse_args(args)
    if _running_in_blender():
        return _run_inside_blender(ns)
    return _relaunch_in_blender(args)


if __name__ == "__main__":
    raise SystemExit(main())
