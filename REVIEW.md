# Review rules for this repository

Review rules on top of the reviewer's default focus. Three things:
which findings are blocking here, which classes to report that the
default focus would otherwise skip, and which are noise. The reasoning
behind the rules lives in `.github/copilot-instructions.md` (its
numbered focus items are cited below) and `CLAUDE.md`, which the
reviewer also receives.

## Always blocking

- **A `run_*` site function that lets an exception escape (§1).**
  `cli.py`'s main loop does not wrap each call, so an escaping
  exception reaches the outer handler and aborts **every remaining site
  in the batch**, not just the failing one. Every existing
  `sites/*.py` module wraps its `run_*` body in a broad `try/except
  Exception`. Do not assume a single uniform block shape when checking
  this — `ookla.py` snapshots inside its own per-attempt retry loop
  rather than in one `finally`.
- **An extraction helper that can raise past its own `try`/`except`
  (§2).** Values are scraped from live third-party DOM that changes
  shape regularly, so the convention is to return `""` on any failure
  and let the caller gate on it — `run_cloudflare`'s `if not download:
  return` before building the payload. A possibly-empty value sent
  straight to a backend without passing through `SenderManager.send()`'s
  empty-value drop belongs here too: that filter is what keeps Zabbix,
  Grafana and OTel consistent.
- **A credential reaching a log line at any level, `debug` included
  (§3).** `[zabbix] api_password`, `[grafana] token`, and OTel
  `headers`, which may carry an `Authorization` value or API key. The
  existing code logs only *whether* a scheme is plaintext
  (`_is_plaintext_remote`) or *that* configuration is incomplete —
  never the secret.
- **A `zapi_lib.ZapiClient` caller that lets an exception escape, or
  that guards only `ImportError` without also wrapping the API call
  (§4).** `SenderManager.set_version_tag()` is optional and must stay
  non-fatal: it no-ops on dry-run, on Zabbix disabled, and on a partial
  credential set, and catches both a missing import and any
  `ZapiError` / `ZapiAuthError` / network failure. A speed test run
  must not fail because a version stamp could not be written.
- **A new optional-backend import that is not lazy (§5).** `grafana`
  (`cramjam`), `otel` (`opentelemetry-*`) and `zabbix-api` (`zapi-lib`)
  are extras, each imported inside its own `try`/`except ImportError`
  that logs the `pip install speedtest-z[...]` hint rather than
  crashing when the section is enabled but the extra is absent.

## Report even though the default focus would not

- **A diff that adds or changes an extraction helper or site runner and
  also touches `tests/` without a failure or edge case (§6)**, as
  advisory: element missing, timeout, or DOM text in an unexpected
  shape. This is precisely the regression class the sites are most
  prone to, since the DOM belongs to somebody else. Judge it from the
  diff only — you receive changed files, so a pull request that leaves
  `tests/` alone may well be covered by tests you were not given.
- **A test that would drive a real browser (§6).** The suite never
  launches Chrome: `speedtest_z.runner.SpeedtestZ` and
  `selenium.webdriver` are mocked through `unittest.mock`, via
  `tests/conftest.py`'s `mock_app` / `mock_config` fixtures.
- **An OTel or Grafana test that hard-fails when the optional
  dependency is absent (§6)**, as advisory. Those tests are written to
  skip cleanly instead.

## Never report

- **MCP-flavored advice.** A content envelope, stdio-safety checks, or
  adversarial-LLM-input handling — none of that applies here. This is a
  CLI that drives a browser and ships metrics, not an MCP server.
- A request to hand-bump `pyproject.toml`'s `version` or edit
  `CHANGELOG.md`. release-please manages both.
- `.deb` / `.rpm` packaging (`debian/`, `rpm/`) and the release or
  publish workflows. Those are release-time concerns, and `CLAUDE.md`'s
  release-please section is authoritative for them rather than
  re-derivation from the workflow YAML.
- Anything `ruff check` or `ruff format` already fails the build on.
  Both gate `speedtest_z/` and `tests/`, so restating a finding costs a
  round trip and no information.
