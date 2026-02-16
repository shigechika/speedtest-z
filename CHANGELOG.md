# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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

[0.4.8]: https://github.com/shigechika/speedtest-z/compare/v0.4.7...v0.4.8
[0.4.7]: https://github.com/shigechika/speedtest-z/compare/v0.4.4...v0.4.7
[0.4.4]: https://github.com/shigechika/speedtest-z/compare/v0.3.0...v0.4.4
[0.3.0]: https://github.com/shigechika/speedtest-z/compare/v0.1.3...v0.3.0
[0.1.3]: https://github.com/shigechika/speedtest-z/releases/tag/v0.1.3
