"""Entrypoint: parse Allure results, triage each failure, write report.

Usage:
    python main.py --allure-results ./allure-results --repo ./my-api-tests \\
        --spec ./openapi.yaml --out ./triage-output
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load variables from a `.env` file in the project root (if present).
# Does nothing if the file is missing, so it's safe in CI too.
load_dotenv(Path(__file__).parent / ".env")

from agent import build_agent  # noqa: E402 — import after load_dotenv
from tools import (
    parse_allure_report,
    set_repo_root,
    set_report_paths,
    set_runner,
    set_spec_path,
)


FAILURE_PROMPT_TEMPLATE = """Triage the following failing API test from an Allure report.

TEST_ID: {test_id}
NAME: {test_name}
STATUS: {status}
DURATION_MS: {duration_ms}
LABELS: {labels}

ERROR MESSAGE:
{error_message}

STACK TRACE:
{stack_trace}

HTTP REQUEST (from Allure attachments, may be truncated):
{request}

HTTP RESPONSE (from Allure attachments, may be truncated):
{response}

Follow this order:
  1. Call get_test_source with the test name to read the test code.
  2. If the failure looks like a response-shape mismatch or an unexpected
     status code, call get_api_spec for the endpoint under test.
  3. Call run_single_test ONCE with this test_id to probe for flakiness.
     - If it now passes with no changes, this is FLAKY.
  4. Call write_fix_proposal exactly once with your verdict. Then STOP.

Do not move on to other failures. One call to write_fix_proposal ends this task.
"""


def _truncate(s: str | None, limit: int) -> str:
    if not s:
        return "(none)"
    s = str(s)
    if len(s) <= limit:
        return s
    return s[:limit] + f"\n... [truncated, {len(s) - limit} chars omitted]"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lightweight AI agent that triages Allure test failures.",
    )
    parser.add_argument(
        "--allure-results",
        required=True,
        help="Path to the allure-results/ directory.",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to the repo containing the tests (for source lookup + re-runs).",
    )
    parser.add_argument(
        "--spec",
        default=None,
        help="Optional OpenAPI spec file (YAML or JSON).",
    )
    parser.add_argument(
        "--out",
        default="./triage-output",
        help="Output directory for report.md and fixes/.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        help="Anthropic model id. Can also be set via ANTHROPIC_MODEL env var.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the first N failures (useful for smoke tests).",
    )
    parser.add_argument(
        "--runner-cmd",
        nargs="+",
        default=None,
        help="Override the test-runner command, e.g. --runner-cmd pytest -xvs",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print agent intermediate steps.",
    )
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        return 2

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Configure the tool layer
    set_repo_root(args.repo)
    set_spec_path(args.spec)
    set_runner(args.repo, args.runner_cmd)
    set_report_paths(out_dir / "report.md", out_dir / "fixes")

    # Parse failures
    print(f"Parsing Allure results from {args.allure_results} ...")
    failures = parse_allure_report(args.allure_results)
    print(f"Found {len(failures)} failing/broken test(s).")

    if args.limit is not None:
        failures = failures[: args.limit]
        print(f"Limited to first {len(failures)}.")

    if not failures:
        print("Nothing to triage.")
        return 0

    agent = build_agent(model=args.model)

    for i, f in enumerate(failures, start=1):
        print(f"\n[{i}/{len(failures)}] Triaging: {f.test_id}")
        prompt_input = FAILURE_PROMPT_TEMPLATE.format(
            test_id=f.test_id,
            test_name=f.test_name,
            status=f.status,
            duration_ms=f.duration_ms,
            labels=f.labels or "{}",
            error_message=_truncate(f.error_message, 800),
            stack_trace=_truncate(f.stack_trace, 2000),
            request=_truncate(f.http.request, 1500),
            response=_truncate(f.http.response, 1500),
        )
        try:
            result = agent.invoke(
                {"messages": [{"role": "user", "content": prompt_input}]},
                config={"recursion_limit": 20},
            )
            if args.verbose:
                # Print the final assistant message
                last = result["messages"][-1]
                content = getattr(last, "content", "")
                if content:
                    print(f"  agent: {content[:300]}")
        except Exception as e:  # noqa: BLE001 - keep going on per-test errors
            print(f"  ERROR triaging {f.test_id}: {e}", file=sys.stderr)

    print(f"\nDone. Report: {out_dir / 'report.md'}")
    print(f"Fixes:        {out_dir / 'fixes'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
