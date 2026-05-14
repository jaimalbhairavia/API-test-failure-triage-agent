"""Tool layer for the Allure triage agent.

The module-level setters (set_repo_root, set_spec_path, set_runner,
set_report_paths) are used by main.py to wire runtime config into the
tools before the agent is invoked. The tools themselves take only the
arguments the LLM needs to produce.
"""

from .allure import parse_allure_report, Failure, HttpExchange
from .source import get_test_source, set_repo_root
from .spec import get_api_spec, set_spec_path
from .runner import run_single_test, set_runner
from .report import write_fix_proposal, set_report_paths

__all__ = [
    "parse_allure_report",
    "Failure",
    "HttpExchange",
    "get_test_source",
    "get_api_spec",
    "run_single_test",
    "write_fix_proposal",
    "set_repo_root",
    "set_spec_path",
    "set_runner",
    "set_report_paths",
]
