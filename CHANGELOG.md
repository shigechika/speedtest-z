# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.12.0](https://github.com/shigechika/speedtest-z/compare/v0.11.0...v0.12.0) (2026-08-08)


### Features

* --headed を --no-headless のエイリアスとして追加 ([8a9a9c6](https://github.com/shigechika/speedtest-z/commit/8a9a9c62379b3414df28e73319c5d1bce5bc5005))
* --man / -m オプションでマニュアル表示を追加 ([065cfc3](https://github.com/shigechika/speedtest-z/commit/065cfc3ee882e7caf499bd37a8f601e4d408e363))
* add .deb packaging with dh-virtualenv and /etc/speedtest-z/ config path ([24af5a4](https://github.com/shigechika/speedtest-z/commit/24af5a423274a8702d311683c521e8fa672fa211))
* add /etc/default/speedtest-z support for systemd option injection ([c93fd1b](https://github.com/shigechika/speedtest-z/commit/c93fd1b9a6b12dd3641933db23e36c86283e470b))
* add config.ini-sample URL to error messages and epilog to --help ([06e97d6](https://github.com/shigechika/speedtest-z/commit/06e97d679c2427c4736e08078b8a3166798296ca))
* add Grafana Cloud integration and improve config.ini design ([1183426](https://github.com/shigechika/speedtest-z/commit/118342649a7d48b1d1369e1bcc5a8b848ea121a1))
* add graphs to Zabbix template (Download/Upload/Latency/Jitter) ([7410a17](https://github.com/shigechika/speedtest-z/commit/7410a17cabde32afe8c1ac845b7d6a15c3cfc380))
* add Homebrew tap support ([1b8ea69](https://github.com/shigechika/speedtest-z/commit/1b8ea692fab2c785562a4a572a5ea6514ecf0af6))
* add OpenTelemetry (OTLP) metrics export support ([9b68ba0](https://github.com/shigechika/speedtest-z/commit/9b68ba0403257add2453cface70a1312de03ded7))
* add pr-gate.yml admission control caller ([#58](https://github.com/shigechika/speedtest-z/issues/58)) ([d18d85a](https://github.com/shigechika/speedtest-z/commit/d18d85a938902ab7d4138b464bdba81a5f5ebcb9))
* add RPM packaging with fpm for RHEL 9 / Rocky Linux 9 ([6ac661a](https://github.com/shigechika/speedtest-z/commit/6ac661aecefaccc184305a7d56e9d8a0833a92a1))
* config.ini 必須化と TTY 確認プロンプトで誤起動を防止 ([a083591](https://github.com/shigechika/speedtest-z/commit/a083591f44ca6c7d887f05a0f8deb467cb466e88))
* depend on zapi-lib for the host-tag feature (+ deb/rpm extras) ([#26](https://github.com/shigechika/speedtest-z/issues/26)) ([dd76345](https://github.com/shigechika/speedtest-z/commit/dd7634544a79ffa06ac8a1945b58c4933258d2af))
* docstring 英語化、python -m 対応、argcomplete タブ補完 ([0a85b0c](https://github.com/shigechika/speedtest-z/commit/0a85b0c83f42011a51616ea8281ff2114c9125e5))
* persist Chrome profile and guard consent dialogs with --yes ([ecc1722](https://github.com/shigechika/speedtest-z/commit/ecc17226874515f077aedf949aa075e55ec0b49d))
* stamp speedtest-z version onto the Zabbix host as a tag ([#24](https://github.com/shigechika/speedtest-z/issues/24)) ([801ec55](https://github.com/shigechika/speedtest-z/commit/801ec5565f496efe4388022524004c7941508a3e))
* ユーザ向けメッセージをロケールに応じて日英切り替え ([b97b508](https://github.com/shigechika/speedtest-z/commit/b97b5089bbc574d2fa10c026638137aaadfdb468))
* 速度テスト結果の投稿用 Issue テンプレートを追加 ([c9ec28a](https://github.com/shigechika/speedtest-z/commit/c9ec28a79f7b512f06fbf052113baab840def6fb))


### Bug Fixes

* adapt ookla and mlab runners to site UI changes, exit 130 on Ctrl-C ([#38](https://github.com/shigechika/speedtest-z/issues/38)) ([6cf6870](https://github.com/shigechika/speedtest-z/commit/6cf68703c9e7ae4fe93810cafd13b3c1b79862f2))
* add build-essential/adduser deps, remove duplicate conffiles ([7e7c71d](https://github.com/shigechika/speedtest-z/commit/7e7c71dd6446a984030e3b7ccf07f1959c940b0a))
* add python3-virtualenv to deb build dependencies ([4422be7](https://github.com/shigechika/speedtest-z/commit/4422be7f6ca1d563beadfcfee81b5e2fc1b3b7fc))
* add stream parameter to _setup_logging() for json/csv stderr output ([a1fa095](https://github.com/shigechika/speedtest-z/commit/a1fa095acb7688daa888f9a201b57d7bec2af741))
* address priority findings from full-branch code review ([#9](https://github.com/shigechika/speedtest-z/issues/9)) ([4944fa4](https://github.com/shigechika/speedtest-z/commit/4944fa4bbed0bfef071da73f4b5f535d9eb0492b))
* CLI でサイト明示指定時は frequency スロットルをスキップ ([11fcf49](https://github.com/shigechika/speedtest-z/commit/11fcf49fa6c764d25865657a326e0786fe4f2d1e))
* exit 143 on SIGTERM and declare interrupt codes in systemd units ([#47](https://github.com/shigechika/speedtest-z/issues/47)) ([c4a9847](https://github.com/shigechika/speedtest-z/commit/c4a98478a845c61e0858f8ba1259b37cc3c60383))
* Google Fiber の URL を HTTP に戻す ([69edd81](https://github.com/shigechika/speedtest-z/commit/69edd81d4511bea5535b74c5d71d4758f87d6b7f))
* Grafana HTTP error handling, config key validation, cloudflare unit check ([319ce3f](https://github.com/shigechika/speedtest-z/commit/319ce3fb2103476b5fa9efc048f35518e93d576d))
* harden deploy/packaging scripts (cron scope, drop unused /var/log) ([#12](https://github.com/shigechika/speedtest-z/issues/12)) ([b24bb71](https://github.com/shigechika/speedtest-z/commit/b24bb71cb4d3a9fa658fabe360673fa51ce87944))
* honor stream=stderr even when logging.ini is loaded ([#18](https://github.com/shigechika/speedtest-z/issues/18)) ([00e6b03](https://github.com/shigechika/speedtest-z/commit/00e6b0379f9aff826bee9533b61811ac5d7e02dd))
* low-severity robustness and hygiene cleanups ([#11](https://github.com/shigechika/speedtest-z/issues/11)) ([8c694af](https://github.com/shigechika/speedtest-z/commit/8c694afca7c534330aebeffd6d46a0c23fd2ea4d))
* make -y/--yes skip the execution confirmation prompt ([#44](https://github.com/shigechika/speedtest-z/issues/44)) ([60c390e](https://github.com/shigechika/speedtest-z/commit/60c390e221b78cb68ec2c6bdec5429cc676f2b98))
* README.md の日本語版リンクテキストを修正 ([c176a7e](https://github.com/shigechika/speedtest-z/commit/c176a7e00cdd4ae465a13456b524d6266687c4a3))
* rewrite ookla server selection for the redesigned UI ([#48](https://github.com/shigechika/speedtest-z/issues/48)) ([a7b74f1](https://github.com/shigechika/speedtest-z/commit/a7b74f1ee0c699e8b147f6f40cd5b0123e77306d))
* skip OtelSender tests when opentelemetry is not installed ([c10c14f](https://github.com/shigechika/speedtest-z/commit/c10c14fc8fc2d57538e3f95864caaed12ccf3056))
* use Sender.send_bulk() for zappix v1.x API compatibility ([b1810de](https://github.com/shigechika/speedtest-z/commit/b1810de71d5e57e6f40dcfd96b94a5541dea3104))


### Refactoring

* extract _init_logging and _confirm_execution from main() ([27024f9](https://github.com/shigechika/speedtest-z/commit/27024f942a103ff669c991d0eca732c04ecc7d28)), closes [#5](https://github.com/shigechika/speedtest-z/issues/5)
* extract SenderManager from SpeedtestZ ([89c0148](https://github.com/shigechika/speedtest-z/commit/89c0148e3d98eb3d5dee7c72030c0c5b4a9b6680)), closes [#4](https://github.com/shigechika/speedtest-z/issues/4)
* replace bare except-pass with logger.debug/exception ([23cc574](https://github.com/shigechika/speedtest-z/commit/23cc5740469aed51514bcba53df8d71182d5c6aa))
* replace OutputCollector monkey-patch with sender interface ([9116e03](https://github.com/shigechika/speedtest-z/commit/9116e03154efee47c2490709f3329c202145ed8d)), closes [#6](https://github.com/shigechika/speedtest-z/issues/6)
* split monolithic main.py into modular package structure ([dd386fc](https://github.com/shigechika/speedtest-z/commit/dd386fc4fe32d021852d019727df8cdd10b3b1f2))

## [0.11.0](https://github.com/shigechika/speedtest-z/compare/v0.10.3...v0.11.0) (2026-08-08)


### Features

* add pr-gate.yml admission control caller ([#58](https://github.com/shigechika/speedtest-z/issues/58)) ([d18d85a](https://github.com/shigechika/speedtest-z/commit/d18d85a938902ab7d4138b464bdba81a5f5ebcb9))

## [0.10.3](https://github.com/shigechika/speedtest-z/compare/v0.10.2...v0.10.3) (2026-07-18)


### Bug Fixes

* exit 143 on SIGTERM and declare interrupt codes in systemd units ([#47](https://github.com/shigechika/speedtest-z/issues/47)) ([c4a9847](https://github.com/shigechika/speedtest-z/commit/c4a98478a845c61e0858f8ba1259b37cc3c60383))
* rewrite ookla server selection for the redesigned UI ([#48](https://github.com/shigechika/speedtest-z/issues/48)) ([a7b74f1](https://github.com/shigechika/speedtest-z/commit/a7b74f1ee0c699e8b147f6f40cd5b0123e77306d))

## [0.10.2](https://github.com/shigechika/speedtest-z/compare/v0.10.1...v0.10.2) (2026-07-18)


### Bug Fixes

* make -y/--yes skip the execution confirmation prompt ([#44](https://github.com/shigechika/speedtest-z/issues/44)) ([60c390e](https://github.com/shigechika/speedtest-z/commit/60c390e221b78cb68ec2c6bdec5429cc676f2b98))

## [0.10.1](https://github.com/shigechika/speedtest-z/compare/v0.10.0...v0.10.1) (2026-07-18)


### Bug Fixes

* adapt ookla and mlab runners to site UI changes, exit 130 on Ctrl-C ([#38](https://github.com/shigechika/speedtest-z/issues/38)) ([6cf6870](https://github.com/shigechika/speedtest-z/commit/6cf68703c9e7ae4fe93810cafd13b3c1b79862f2))

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
