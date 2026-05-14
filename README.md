# Allure Triage Agent (pilot)

A lightweight LangChain agent that reads an Allure report, classifies
each failing test, proposes a fix, and does a single re-run to detect
flakes. Produces a markdown report and (optionally) patch files for a
human to review and apply.

## What problem does this agent solve?

CI/CD test failures are inevitable — whether caused by flakiness, spec drift, authentication issues, or genuine regressions. At high development velocity, where a pipeline runs on every pull request, systematically investigating each failure becomes impractical. Failure attribution gets deprioritized, tests get skipped, and pipelines gradually lose credibility. Left unchecked, this erodes release confidence and removes the safety net that automated testing is meant to provide.

This agent addresses that problem directly. It automatically triages test failures, classifies each one by root cause, and produces a structured report with actionable fix suggestions — giving engineering teams the signal they need without the manual investigation overhead.

## What it does

For every failure or broken test in `allure-results/`:

1. Parses the result JSON + attached request/response bodies.
2. Hands the failure to a tool-calling agent with four tools:
   - `get_test_source` — grep-finds the test function in your repo.
   - `get_api_spec` — returns the OpenAPI path object (optional).
   - `run_single_test` — re-runs that one test to probe for flakiness.
   - `write_fix_proposal` — records the agent's verdict.
3. The agent classifies the failure as one of
   `SPEC_DRIFT | AUTH | ENVIRONMENT | TEST_BUG | FLAKY` and writes a
   proposed fix (and, when confident, a `.patch` file).
4. A markdown report is written to `<out>/report.md`.

The agent **does not apply fixes**. That's a human step by design for
the pilot.

## Install

```bash
pip install -r requirements.txt
cp .env.example .env      # then edit .env with your real key
```

`.env` is git-ignored. `python-dotenv` loads it at startup; you can
also just `export ANTHROPIC_API_KEY=...` the old-fashioned way if you
prefer — either works.

## Run

```bash
python main.py \
  --allure-results /path/to/allure-results \
  --repo           /path/to/your/api-tests \
  --spec           /path/to/openapi.yaml \
  --out            ./triage-output \
  --limit 5
```

`--spec` is optional; if omitted, `get_api_spec` returns a "no spec
configured" message and the agent falls back to stack-trace evidence.

`--limit` caps how many failures to process — useful for a first run.

`--runner-cmd` overrides the re-run invocation. Default is
`pytest -xvs --tb=short --no-header`. To use `newman`:

```bash
--runner-cmd newman run collection.json --folder
```

## Output

```
triage-output/
  report.md           # one section per failure
  fixes/
    <test_id>.patch   # only when the agent proposed a concrete diff
```

## Assumptions

- Tests run from the machine you're running the agent on (not a
  remote CI runner).
- Default test runner is `pytest`; override with `--runner-cmd` for
  newman / jest / mocha / etc.
- `get_test_source` uses regex on `def <func>(`. It finds the right
  function ~always for normal test suites; parametrized or
  dynamically-generated tests may need manual lookup.
- No git or deploy-log access in this pilot — attribution relies on
  the test, the stack trace, and the OpenAPI spec.

## What to add next (when the pilot has earned it)

1. **Git correlation** — a `git_log_for_file(path, since)` tool. Biggest
   attribution lift for the least code.
2. **Clustering** before classification, once a run has >20 failures.
3. **Auto-apply allowlist** — e.g. auth-token refresh.
4. **Memory** — persist resolved-failure signatures so the next run
   recognises repeats.

## File tour

```
allure-triage-agent/
  main.py             # CLI entrypoint, failure loop
  agent.py            # LangChain tool-calling agent setup
  prompts/system.txt  # the agent's system prompt
  tools/
    allure.py         # parse_allure_report (run outside the LLM loop)
    source.py         # get_test_source
    spec.py           # get_api_spec
    runner.py         # run_single_test
    report.py         # write_fix_proposal
  sample/             # tiny fixtures for a smoke test (see sample/README.md)
```

## Smoke test

See `sample/README.md` for a self-contained example with two fabricated
failures and a tiny test repo.
