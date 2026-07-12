# Repository overview

`speedtest-z` is a Selenium-driven CLI that runs speed tests against 8 public
sites (Cloudflare, Netflix/fast.com, Google Fiber, Ookla, Box-test, M-Lab,
USEN, iNonius) in a real Chrome browser, scrapes the on-page result numbers,
and reports them to Zabbix (via `zappix`, trapper protocol), and optionally
Grafana Cloud (Prometheus Remote Write) and/or an OTLP endpoint. It typically
runs unattended on a schedule (systemd timer / cron), not interactively. It is
**not** an MCP server and has no LLM-facing surface — do not apply
MCP/tool-envelope/adversarial-input review patterns from other repos in this
family here.

See `CLAUDE.md` for the authoritative command list, architecture map, and
config.ini design — read it before reviewing changes to `runner.py`,
`sender.py`, or any `sites/*.py`.

# Build & validate

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[test,dev]"
ruff check speedtest_z/ tests/
ruff format --check speedtest_z/ tests/
mypy speedtest_z/
pytest tests/ -v
```

This mirrors `.github/workflows/ci.yml` (matrix over Python 3.10-3.14, plus an
`actionlint` job on the workflows themselves). Unlike some sibling repos,
**style and typing are enforced here** — `ruff check`, `ruff format --check`,
and `mypy speedtest_z/` all gate the PR. Do flag formatting/lint/type issues
in this repo.

# What to focus review on in this repo

## 1. Each `run_*` site function must contain its own failures

`cli.py`'s main loop (`for site in sites: runner(app)`) does **not** wrap each
call — an exception that escapes a `run_xxx()` propagates to the outer
`except Exception: logger.exception("Fatal Error"); sys.exit(1)` and aborts
every remaining site for that run, not just the failing one. Every existing
`sites/*.py` module wraps its `run_*` body in a broad
`try/except Exception` (most also emit a debug snapshot via
`app.take_snapshot(...)` on failure or timeout — `ookla.py` does this inside
its own per-attempt retry loop instead of a single `finally`, so don't assume
the same block shape everywhere). Flag any new/modified `run_*` that lets an
exception escape uncaught, since the actual failure mode is "one broken site
kills the rest of the batch," not a crash of that one test.

## 2. Parsing robustness: the extraction helpers must fail soft, not raise

Result values are scraped from live third-party DOM (e.g. `cloudflare.py`'s
`_extract_by_label`), which regularly changes shape. The existing convention
is: extraction helpers return `""` on any failure to find/parse a value
(never raise past their own `try/except`), and callers gate on that — e.g.
`run_cloudflare` checks `if not download: return` before building the metrics
payload. `SenderManager.send()` then drops any item whose `value` is empty
before dispatching to backends, keeping Zabbix/Grafana/OTel consistent. Flag
a new extraction path that would raise on a missing/changed element, or that
sends a possibly-empty value straight to a backend without going through this
filtering.

## 3. Zabbix/Grafana/OTel credentials must never be logged, at any level

`[zabbix] api_password`, `[grafana] token`, and OTel `headers` (may carry
`Authorization`/API keys) are read from `config.ini`
(`config.ini-sample` documents the shape; the real file is gitignored). Flag
any diff that logs these values, including at `debug` — the existing code
only logs *whether* a scheme is plaintext (`_is_plaintext_remote` in
`sender.py`) or *that* config is incomplete, never the secret itself.

## 4. The optional Zabbix API path (`zapi-lib`) must stay non-fatal

`SenderManager.set_version_tag()` (called from `runner.stamp_version()` after
all sites finish) stamps `speedtest-z=<version>` onto the Zabbix host via the
optional `zapi-lib` package, separate from the trapper send path. It no-ops
when dry-run, when Zabbix is disabled, or when `api_url`/`api_user`/
`api_password` aren't all set (warns on a partial set), and both a missing
`zapi_lib` import and any exception during the API call
(`zapi_lib.ZapiError`/`ZapiAuthError`, or a network failure) are caught and
logged, never raised. A new caller of `zapi_lib.ZapiClient` that lets an
exception escape, or that only no-ops on `ImportError` without also guarding
the API call itself, breaks this contract.

## 5. Optional-dependency extras must degrade gracefully, not crash

`grafana` (`cramjam`), `otel` (`opentelemetry-*`), and `zabbix-api`
(`zapi-lib`) are all optional extras, each imported lazily inside its own
`try/except ImportError` that logs the install hint
(`pip install speedtest-z[...]`) rather than crashing when the section is
enabled but the extra isn't installed. `SenderManager.__init__` does this for
`grafana`/`otel`; the `zabbix-api` (`zapi-lib`) import happens on the
version-tag path (`SenderManager.set_version_tag()`, see §4), not in
`__init__`. Hold new optional-backend code to the same lazy,
install-hint-logging pattern.

## 6. Test conventions

- Tests never launch a real browser: `speedtest_z.runner.SpeedtestZ` and
  `selenium.webdriver` are mocked via `unittest.mock.MagicMock`/`patch`
  (see `tests/conftest.py`'s `mock_app`/`mock_config` fixtures and
  `tests/test_sites/*.py`). A new site-runner test that tries to drive a real
  Chrome instance is inconsistent with the suite.
- A new/changed extraction helper or site runner needs a test covering both
  the happy path and at least one failure/edge case (element missing,
  timeout, DOM text in an unexpected shape) — this is exactly the class of
  regression the sites are most prone to.
- OTel/Grafana tests are written to skip cleanly when the optional dependency
  isn't installed; don't add a test that hard-fails the suite in that case.

# Out of scope for review comments

- `pyproject.toml`'s `version` field and `CHANGELOG.md` are managed by
  release-please — don't suggest manually bumping either.
- `.deb`/`.rpm` packaging (`debian/`, `rpm/`) and the release/publish
  workflows are release-time concerns; treat `CLAUDE.md`'s release-please
  section as authoritative rather than re-deriving packaging behavior from
  the workflow YAML.
- Don't ask for an MCP-style content envelope, stdio-safety checks, or
  adversarial-LLM-input handling — none apply to this repo.
