# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.10.0](https://github.com/shigechika/speedtest-z/compare/v0.9.0...v0.10.0) (2026-06-04)


### Features

* depend on zapi-lib for the host-tag feature (+ deb/rpm extras) ([#26](https://github.com/shigechika/speedtest-z/issues/26)) ([dd76345](https://github.com/shigechika/speedtest-z/commit/dd7634544a79ffa06ac8a1945b58c4933258d2af))

## [0.9.0](https://github.com/shigechika/speedtest-z/compare/v0.8.5...v0.9.0) (2026-06-04)


### Features

* stamp speedtest-z version onto the Zabbix host as a tag ([#24](https://github.com/shigechika/speedtest-z/issues/24)) ([801ec55](https://github.com/shigechika/speedtest-z/commit/801ec5565f496efe4388022524004c7941508a3e))

## [0.8.5](https://github.com/shigechika/speedtest-z/compare/v0.8.4...v0.8.5) (2026-06-02)


### Bug Fixes

* honor stream=stderr even when logging.ini is loaded ([#18](https://github.com/shigechika/speedtest-z/issues/18)) ([00e6b03](https://github.com/shigechika/speedtest-z/commit/00e6b0379f9aff826bee9533b61811ac5d7e02dd))

## [0.8.4](https://github.com/shigechika/speedtest-z/compare/v0.8.3...v0.8.4) (2026-06-02)


### Bug Fixes

* address priority findings from full-branch code review ([#9](https://github.com/shigechika/speedtest-z/issues/9)) ([4944fa4](https://github.com/shigechika/speedtest-z/commit/4944fa4bbed0bfef071da73f4b5f535d9eb0492b))
* harden deploy/packaging scripts (cron scope, drop unused /var/log) ([#12](https://github.com/shigechika/speedtest-z/issues/12)) ([b24bb71](https://github.com/shigechika/speedtest-z/commit/b24bb71cb4d3a9fa658fabe360673fa51ce87944))
* low-severity robustness and hygiene cleanups ([#11](https://github.com/shigechika/speedtest-z/issues/11)) ([8c694af](https://github.com/shigechika/speedtest-z/commit/8c694afca7c534330aebeffd6d46a0c23fd2ea4d))


### Documentation

* add Homebrew bottle availability note to README ([0555cd6](https://github.com/shigechika/speedtest-z/commit/0555cd629a855d1a36572a6256c1a393056d32c8))
* add otel install command and test skip note to CLAUDE.md ([7b57bee](https://github.com/shigechika/speedtest-z/commit/7b57beeeafdfe8040aee232bddc9bf10c635e43b))
* add troubleshooting section to README ([ad0eedf](https://github.com/shigechika/speedtest-z/commit/ad0eedfc6807b78036abfc7ec14810ee2a96dc84)), closes [#8](https://github.com/shigechika/speedtest-z/issues/8)
* update CLAUDE.md architecture for SenderManager and MetricSender ([391ae97](https://github.com/shigechika/speedtest-z/commit/391ae97b168fb82f3531a1b798d8bb532bf518b0))
* update example output with confirmation prompt, remove JANOG57 reference ([aa675db](https://github.com/shigechika/speedtest-z/commit/aa675db92e41cd6d94e50c81f6a2bff846915062))

## [0.8.3] - 2026-02-25

### Added
- RHEL 9 / Rocky Linux 9 / AlmaLinux 9 `.rpm` package building with fpm (`rpm/` directory)
- `.github/workflows/rpm.yml` CI for building `.rpm` packages on Rocky Linux 9 container
- `workflow_dispatch` trigger for both `.deb` and `.rpm` workflows (manual build testing without tag)
- `uv` installation instructions in README

### Changed
- Logging: bare `except: pass` replaced with `logger.debug` in site runners for easier troubleshooting
- Logging: `logger.error` → `logger.exception` for Zabbix/Grafana/OTel send failures (includes stack trace)
- Logging: cramjam/opentelemetry import failures raised from `warning` to `error`
- Logging: dryrun buffer output lowered from `info` to `debug`
- `deploy/speedtest-z.service` generalized for reusable template
- `deploy/speedtest-z.timer` added `RandomizedDelaySec=180`
- `grafana-dashboard.json` line interpolation smooth, lineWidth 1, pointSize 3

### Fixed
- `ruff format` violation in `runner.py` that caused CI failure in v0.8.2

## [0.8.2] - 2026-02-25

### Note
- CI (`ruff format --check`) failed due to formatting violation in `runner.py`. Packages (PyPI, .deb, .rpm) were published successfully. Superseded by v0.8.3.

## [0.8.1] - 2026-02-24

### Fixed
- `.deb` CI: add `python3-virtualenv` to build dependencies

## [0.8.0] - 2026-02-24

### Added
- Debian/Ubuntu `.deb` package building with dh-virtualenv (`debian/` directory)
- `.github/workflows/deb.yml` CI for building `.deb` packages (jammy, noble)
- `/etc/speedtest-z/` as system-wide config path fallback
- System user `speedtest-z`, directories `/var/lib/speedtest-z/`, `/var/log/speedtest-z/`
- Hardened systemd service with `ProtectSystem=strict`, `PrivateTmp=yes`, etc.
- `/etc/cron.d/speedtest-z-cleaner` for Chrome temp file cleanup

### Changed
- Config file search order: CLI → CWD → `~/.config/speedtest-z/` → `/etc/speedtest-z/`

## [0.7.1] - 2026-02-23

### Fixed
- CI: skip OtelSender unit tests when `opentelemetry` is not installed

## [0.7.0] - 2026-02-23

### Added
- OpenTelemetry (OTLP) metrics export via `speedtest_z/otel.py` (OtelSender)
- `[otel]` config section with `enable`, `endpoint`, `headers`
- `opentelemetry-*` optional dependency: `pip install speedtest-z[otel]`
- OTel unit tests (16 new tests, 182 total)
- Graceful fallback when `opentelemetry` is not installed
- OTel provider shutdown in `close()` for clean exit

### Changed
- `send_results()` now sends to all 3 backends: Zabbix, Grafana, OTel
- `--dry-run` suppresses all backend sending (Zabbix, Grafana, OTel)

## [0.6.2] - 2026-02-23

### Added
- Zabbix template graphs: Download Speed, Upload Speed, Latency, Jitter

### Fixed
- `grafana.py`: HTTP error response body lost on push failure (now logs status code and body)
- `runner.py`: missing `[grafana]` config keys (`remote_write_url`, `username`, `token`) crashed startup with `NoOptionError`
- `cloudflare.py`: microsecond unit check `"u" in unit_str` was too broad; tightened to exact `"us"` match

### Changed
- `logging.ini` console handler switched from stdout to stderr

## [0.6.1] - 2026-02-22

### Fixed
- `_setup_logging()` missing `stream` parameter causing TypeError on startup

## [0.6.0] - 2026-02-22

### Added
- Grafana Cloud integration via Prometheus Remote Write (`speedtest_z/grafana.py`)
- `[grafana]` config section with `enable`, `remote_write_url`, `username`, `token`
- `[zabbix] enable` flag to control Zabbix sending (default `false`)
- `cramjam` optional dependency: `pip install speedtest-z[grafana]`
- Comprehensive tests for Protobuf encoder, GrafanaSender, and config compatibility (20 new tests, 166 total)

### Changed
- `dryrun` config key renamed to `dry_run` (old name still supported as fallback)
- `send_to_zabbix()` renamed to `send_results()` across all site runners and CLI
- `--dry-run` now suppresses both Zabbix and Grafana sending consistently
- `--output json/csv` outputs to stdout only (no backend sending)
- README.md / README.ja.md updated with Grafana Cloud setup instructions

### Removed
- `grafana_push.py` standalone script (functionality moved into `speedtest_z/grafana.py`)

## [0.5.1] - 2026-02-22

### Fixed
- README.md / README.ja.md に `--check` と `--output` オプションの説明を追加

## [0.5.0] - 2026-02-22

### Added
- `--check` flag: verify site URL reachability via HTTP HEAD without launching Chrome
- `--output json` / `--output csv`: structured output to stdout (Zabbix send is skipped)
- `ruff` linter and formatter with CI integration
- Type hints throughout with `ZabbixItem` TypedDict (`speedtest_z/types.py`)
- Per-site unit tests under `tests/test_sites/` (137 tests total, up from 76)
- `tests/test_snapshot.py`, `tests/test_healthcheck.py`, `tests/test_output.py`
- `mock_driver` and `mock_app` shared fixtures in `conftest.py`

### Changed
- **Breaking:** split monolithic `main.py` (1650 lines) into modular package structure:
  - `cli.py` (CLI entry point), `runner.py` (SpeedtestZ core), `config.py`, `i18n.py`
  - `sites/` package with one module per site (cloudflare, netflix, google, ookla, boxtest, mlab, usen, inonius)
- Entry point changed from `speedtest_z.main:main` to `speedtest_z.cli:main`
- Site runners are now standalone functions (`run_xxx(app)`) instead of class methods
- CI installs `dev` extras and runs `ruff check` / `ruff format --check`

### Removed
- `speedtest_z/main.py` (replaced by modular structure)

## [0.4.9] - 2026-02-16

### Fixed
- Zabbix send failure: use `Sender.send_bulk()` instead of removed `Sender.send()` (zappix v1.x API)

## [0.4.8] - 2026-02-16

### Added
- Persistent Chrome profile to retain cookies and settings across runs
- Automatic consent dialog handling for headless environments
- `/etc/default/speedtest-z` support for systemd option injection via `$SPEEDTEST_Z_OPTS`

## [0.4.7] - 2026-02-15

### Added
- GitHub URL for `config.ini-sample` in config-not-found error messages
- Project URL (`epilog`) in `--help` output

### Changed
- `config.ini-sample`: default `headless` to `false`, comments to English
- README config examples updated to match `config.ini-sample`

## [0.4.4] - 2026-02-15

### Added
- Locale-based message switching (Japanese/English) using `_LANG_JA` flag and `_MESSAGES` dictionary
- TTY confirmation prompt before connecting to test sites
- `config.ini` required check at startup (exit with error if not found)
- CHANGELOG, README badges, and GitHub Releases workflow
- 8 new i18n tests (67 tests total)

### Changed
- User-facing messages now use `_msg()` helper for consistent localization
- `_show_manual()` locale detection unified with module-level `_LANG_JA`

## [0.3.0] - 2026-02-13

### Added
- `--man` / `-m` option for manual display
- `python -m speedtest_z` support
- argcomplete tab completion (optional dependency)
- Unit tests (42 tests) with mock-based testing
- CI pytest integration

### Changed
- Standardized all docstrings to English

## [0.1.3] - 2026-02-12

### Added
- Initial release
- Automated speed testing on 8 sites (Cloudflare, Netflix, Google Fiber, Ookla, Box-test, M-Lab, USEN, iNonius)
- Zabbix trapper integration via zappix
- Probability-based frequency throttling per site
- Screenshot capture for debugging
- Headless/GUI Chrome mode
- CLI with `--dry-run`, site selection, `--headed` alias, and more
- systemd timer deployment files
- PyPI release workflow (TestPyPI + PyPI)

[0.8.3]: https://github.com/shigechika/speedtest-z/compare/v0.8.2...v0.8.3
[0.8.2]: https://github.com/shigechika/speedtest-z/compare/v0.8.1...v0.8.2
[0.8.1]: https://github.com/shigechika/speedtest-z/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/shigechika/speedtest-z/compare/v0.7.1...v0.8.0
[0.7.1]: https://github.com/shigechika/speedtest-z/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/shigechika/speedtest-z/compare/v0.6.2...v0.7.0
[0.6.2]: https://github.com/shigechika/speedtest-z/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/shigechika/speedtest-z/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/shigechika/speedtest-z/compare/v0.5.1...v0.6.0
[0.5.1]: https://github.com/shigechika/speedtest-z/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/shigechika/speedtest-z/compare/v0.4.9...v0.5.0
[0.4.9]: https://github.com/shigechika/speedtest-z/compare/v0.4.8...v0.4.9
[0.4.8]: https://github.com/shigechika/speedtest-z/compare/v0.4.7...v0.4.8
[0.4.7]: https://github.com/shigechika/speedtest-z/compare/v0.4.4...v0.4.7
[0.4.4]: https://github.com/shigechika/speedtest-z/compare/v0.3.0...v0.4.4
[0.3.0]: https://github.com/shigechika/speedtest-z/compare/v0.1.3...v0.3.0
[0.1.3]: https://github.com/shigechika/speedtest-z/releases/tag/v0.1.3
