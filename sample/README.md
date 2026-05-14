# Sample smoke test

Two fabricated failures for a fake "users/orders" API. Running the agent
against them is the quickest way to confirm your setup works end-to-end.

From the project root:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
pip install -r requirements.txt

python main.py \
  --allure-results sample/allure-results \
  --repo           sample/repo \
  --spec           sample/spec/openapi.yaml \
  --out            sample/triage-output \
  --verbose
```

The re-run step will fail (there's no live API) — that's expected.
The agent should still classify both failures and write a report:

- `test_user_creation_returns_201` — test asserts 201 but the OpenAPI
  spec documents 200, and the real response is 200. Expected label:
  **TEST_BUG**.
- `test_list_orders_requires_auth` — request is sent without a bearer
  token and the server returns 401; the spec requires `bearerAuth`.
  Expected label: **AUTH** (or **TEST_BUG** — the agent should note
  both interpretations are plausible).

Output lands in `sample/triage-output/report.md`.
