"""get_test_source tool: find and return the source of a test function.

Simple strategy: regex-match `def <name>(` across the repo's test files.
Good enough for the pilot; no AST, no module resolution.
"""

from __future__ import annotations

import re
from pathlib import Path

from langchain_core.tools import tool

_REPO_ROOT: Path = Path(".")


def set_repo_root(path: str | Path) -> None:
    """Configure which directory get_test_source walks."""
    global _REPO_ROOT
    _REPO_ROOT = Path(path).resolve()


@tool
def get_test_source(test_name: str) -> str:
    """Look up the source code of a test function by name.

    Args:
        test_name: Test function name or Allure full-name. Anything like
            "tests.test_users.test_login" or "TestUsers::test_login" works —
            only the final segment is used.

    Returns:
        The function definition with surrounding context, or a not-found
        message.
    """
    func_name = _extract_func_name(test_name)
    if not func_name:
        return f"Could not derive function name from '{test_name}'."

    # Note: use [ \t]* (not \s*) so we don't accidentally match the
    # blank line preceding a top-level `def`.
    pattern = re.compile(
        rf"^[ \t]*(async[ \t]+)?def[ \t]+{re.escape(func_name)}[ \t]*\(",
        re.MULTILINE,
    )

    # Prefer test_*.py files, fall back to any .py
    for globs in (("test_*.py", "*_test.py"), ("*.py",)):
        for pat in globs:
            for py_file in _REPO_ROOT.rglob(pat):
                if any(part.startswith(".") for part in py_file.parts):
                    continue
                try:
                    content = py_file.read_text(errors="ignore")
                except (OSError, UnicodeDecodeError):
                    continue
                m = pattern.search(content)
                if not m:
                    continue
                snippet = _extract_function_block(content, m.start())
                rel = py_file.relative_to(_REPO_ROOT)
                return f"Found in {rel}:\n\n{snippet}"

    return f"Could not find test source for '{test_name}' under {_REPO_ROOT}."


def _extract_func_name(test_id: str) -> str:
    # Examples:
    #   tests.api.test_users.test_login   -> test_login
    #   tests/api/test_users.py::test_login -> test_login
    #   TestUsers#test_login              -> test_login
    for sep in ("::", "#"):
        if sep in test_id:
            test_id = test_id.split(sep)[-1]
    return test_id.split(".")[-1].strip()


def _extract_function_block(content: str, start_offset: int) -> str:
    """Return the function body starting at the matched `def ...` line.

    Stops at the next top-level (same-indent) def/class/decorator, or EOF.
    """
    lines = content.split("\n")
    start_line = content[:start_offset].count("\n")

    def indent_of(s: str) -> int:
        return len(s) - len(s.lstrip())

    base_indent = indent_of(lines[start_line])
    end_line = len(lines)
    for i in range(start_line + 1, len(lines)):
        line = lines[i]
        if not line.strip():
            continue
        ind = indent_of(line)
        if ind <= base_indent:
            stripped = line.lstrip()
            if stripped.startswith(("def ", "async def ", "class ", "@")):
                end_line = i
                break

    # Cap snippet size
    block = "\n".join(lines[start_line:end_line])
    if len(block) > 4000:
        block = block[:4000] + "\n... [truncated]"
    return block
