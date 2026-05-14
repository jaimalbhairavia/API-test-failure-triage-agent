"""Sample product tests — fabricated for the triage-agent smoke test."""

import requests

BASE = "http://localhost:8080"


def test_search_products():
    resp = requests.get(f"{BASE}/products", params={"q": "widget"})
    assert resp.status_code == 200
    assert len(resp.json()) > 0
