"""run_single_test tool: re-execute one test and return PASS/FAIL.

Defaults to pytest; override via set_runner to point at newman, jest,
mocha, etc. Always scoped to a single test id so the agent cannot
accidentally rerun the full suite.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Optional

from langchain_core.tools import tool

_REPO_ROOT: Path = Path(".")
_RUNNER_CMD: List[str] = ["pytest", "-xvs", "--tb=short", "--no-header"]
_TIMEOUT_SEC: int = 120


def set_runner(
    repo_root: str | Path,
    command: Optional[List[str]] = None,
    timeout_sec: int = 120,
) -> None:
    """Wire up the runner. `command` should include all flags but NOT the test id."""
    global _REPO_ROOT, _RUNNER_CMD, _TIMEOUT_SEC
    _REPO_ROOT = Path(repo_root).resolve()
    if command:
        _RUNNER_CMD = command
    _TIMEOUT_SEC = timeout_sec


@tool
def run_single_test(test_id: str) -> str:
    """Re-run a single test and return its outcome.

    Use this to detect flakiness (a test that passes on clean re-run with
    no code change is FLAKY, not fixed). This tool does NOT apply patches.

    Args:
        test_id: Runner-specific node id. For pytest:
            "tests/test_users.py::test_login".

    Returns:
        A string beginning with "PASS" or "FAIL", followed by the tail of
        the runner's output (last ~1500 chars).
    """
    try:
        result = subprocess.run(
            _RUNNER_CMD + [test_id],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        return f"FAIL: runner timed out after {_TIMEOUT_SEC}s"
    except FileNotFoundError:
        return (
            f"FAIL: runner executable not found "
            f"(tried '{_RUNNER_CMD[0]}' in {_REPO_ROOT})"
        )
    except OSError as exc:
        return f"FAIL: could not launch runner ({exc})"

    output = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
    output = output.strip()
    tail = output[-1500:] if len(output) > 1500 else output

    if result.returncode == 0:
        return f"PASS\n\n{tail}"
    return f"FAIL (exit {result.returncode})\n\n{tail}"
