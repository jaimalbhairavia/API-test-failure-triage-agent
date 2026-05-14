"""Parse an allure-results/ directory into a list of Failure records.

Allure emits one `<uuid>-result.json` per test case. Attachments (request
bodies, response bodies, logs) live alongside as `<uuid>-attachment.<ext>`
and are referenced from each result's `attachments[].source` field, and
sometimes nested inside `steps[].attachments[]`.
"""

import json
from pathlib import Path
from typing import List, Optional, Union

from pydantic import BaseModel, Field


class HttpExchange(BaseModel):
    request: Optional[str] = None
    response: Optional[str] = None


class Failure(BaseModel):
    test_id: str
    test_name: str
    status: str  # "failed" or "broken"
    error_message: str = ""
    stack_trace: str = ""
    http: HttpExchange = Field(default_factory=HttpExchange)
    duration_ms: int = 0
    labels: dict = Field(default_factory=dict)
    attachments: List[str] = Field(default_factory=list)


FAILED_STATUSES = {"failed", "broken"}


def parse_allure_report(results_dir: Union[str, Path]) -> List[Failure]:
    """Return only failing/broken tests from an allure-results directory."""
    results_path = Path(results_dir)
    if not results_path.is_dir():
        raise FileNotFoundError(f"Allure results directory not found: {results_path}")

    failures: List[Failure] = []
    for result_file in sorted(results_path.glob("*-result.json")):
        try:
            data = json.loads(result_file.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        status = data.get("status", "")
        if status not in FAILED_STATUSES:
            continue

        status_details = data.get("statusDetails", {}) or {}
        labels = {l.get("name", ""): l.get("value", "") for l in data.get("labels", [])}

        http = _extract_http(data.get("attachments", []), results_path)
        if not (http.request or http.response):
            http = _extract_http_from_steps(data.get("steps", []), results_path)

        failures.append(
            Failure(
                test_id=data.get("fullName") or data.get("name") or result_file.stem,
                test_name=data.get("name", ""),
                status=status,
                error_message=status_details.get("message", "") or "",
                stack_trace=status_details.get("trace", "") or "",
                http=http,
                duration_ms=max(0, int(data.get("stop", 0)) - int(data.get("start", 0))),
                labels=labels,
                attachments=[a.get("name", "") for a in data.get("attachments", [])],
            )
        )

    return failures


def _extract_http(attachments, base_path: Path) -> HttpExchange:
    req: Optional[str] = None
    res: Optional[str] = None
    for att in attachments or []:
        name = (att.get("name") or "").lower()
        source = att.get("source") or ""
        if not source:
            continue
        file_path = base_path / source
        if not file_path.exists():
            continue
        try:
            content = file_path.read_text(errors="ignore")
        except OSError:
            continue
        if req is None and "request" in name:
            req = content
        elif res is None and "response" in name:
            res = content
    return HttpExchange(request=req, response=res)


def _extract_http_from_steps(steps, base_path: Path) -> HttpExchange:
    for step in steps or []:
        http = _extract_http(step.get("attachments", []), base_path)
        if http.request or http.response:
            return http
        inner = _extract_http_from_steps(step.get("steps", []), base_path)
        if inner.request or inner.response:
            return inner
    return HttpExchange()
