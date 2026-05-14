"""Sample API tests — fabricated for the triage-agent smoke test."""

import requests

BASE = "http://localhost:8080"


def test_user_creation_returns_201():
    resp = requests.post(f"{BASE}/users", json={"name": "alice"})
    assert resp.status_code == 201
    assert "id" in resp.json()


def test_list_orders_requires_auth():
    resp = requests.get(f"{BASE}/orders")
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_get_user_returns_id():
    resp = requests.get(f"{BASE}/users/u-42")
    body = resp.json()
    assert "id" in body
