"""write_fix_proposal tool: append a triage entry to the markdown report.

Optionally saves a unified diff as a .patch file under fixes/. Never
applies the patch — that's a human step.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

_REPORT_PATH: Path = Path("report.md")
_FIXES_DIR: Path = Path("fixes")


def set_report_paths(report_path: str | Path, fixes_dir: str | Path) -> None:
    """Configure output locations. Creates fresh report + fixes dir."""
    global _REPORT_PATH, _FIXES_DIR
    _REPORT_PATH = Path(report_path)
    _FIXES_DIR = Path(fixes_dir)
    _REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _FIXES_DIR.mkdir(parents=True, exist_ok=True)
    # Reset report on each run
    _REPORT_PATH.write_text(
        f"# Allure Triage Report\n\n_Generated: {datetime.now().isoformat(timespec='seconds')}_\n\n"
    )


@tool
def write_fix_proposal(
    test_id: str,
    category: str,
    confidence: float,
    evidence: str,
    proposed_fix: str,
    patch: Optional[str] = None,
    rerun_outcome: Optional[str] = None,
) -> str:
    """Record a classification and proposed fix for one failing test.

    Call this EXACTLY ONCE per failure, as your final step.

    Args:
        test_id: Test identifier from the Allure record.
        category: One of SPEC_DRIFT, AUTH, ENVIRONMENT, TEST_BUG, FLAKY.
        confidence: Your confidence in the classification (0.0 to 1.0).
        evidence: What signals led to this classification. Cite the stack
            trace line, the error message, the spec mismatch, etc.
        proposed_fix: Plain-English description of the change a human
            should make. Include file path and line numbers when known.
        patch: Optional unified diff. If provided, it is saved to fixes/
            as a .patch file. Do NOT apply it.
        rerun_outcome: Optional summary of what happened when you called
            run_single_test ("passed", "failed with same error", etc.).

    Returns:
        "OK" on success.
    """
    category = category.upper().strip()
    confidence = max(0.0, min(1.0, float(confidence)))

    entry = [
        f"## `{test_id}`\n",
        f"- **Category:** {category}",
        f"- **Confidence:** {confidence:.2f}",
    ]
    if rerun_outcome:
        entry.append(f"- **Re-run outcome:** {rerun_outcome}")
    entry.append("")
    entry.append("**Evidence**\n")
    entry.append(evidence.strip())
    entry.append("")
    entry.append("**Proposed fix**\n")
    entry.append(proposed_fix.strip())
    entry.append("")

    if patch and patch.strip():
        safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in test_id)[:120]
        patch_file = _FIXES_DIR / f"{safe}.patch"
        patch_file.write_text(patch if patch.endswith("\n") else patch + "\n")
        entry.append(f"**Patch saved:** `fixes/{patch_file.name}`\n")
        entry.append("```diff")
        entry.append(patch.strip())
        entry.append("```")
        entry.append("")

    entry.append("---\n")

    with _REPORT_PATH.open("a") as f:
        f.write("\n".join(entry))

    return "OK"
