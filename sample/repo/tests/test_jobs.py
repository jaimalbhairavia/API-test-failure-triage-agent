"""Sample async-job tests — fabricated for the triage-agent smoke test."""

import time
import requests

BASE = "http://localhost:8080"
POLL_INTERVAL = 2
MAX_POLLS = 10


def test_async_job_completes():
    resp = requests.post(f"{BASE}/jobs", json={"type": "export"})
    job_id = resp.json()["job_id"]

    status = "pending"
    for _ in range(MAX_POLLS):
        status = requests.get(f"{BASE}/jobs/{job_id}").json()["status"]
        if status == "completed":
            break
        time.sleep(POLL_INTERVAL)

    assert status == "completed", (
        f"job did not complete in time (last status: {status})"
    )
