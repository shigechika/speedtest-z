# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.3.0] - 2026-02-13

### Changed
- Standardized all docstrings to English

### Added
- `python -m speedtest_z` support
- argcomplete tab completion (optional dependency)

## [0.2.0] - 2026-02-13

### Added
- `--man` / `-m` option for manual display
- Unit tests (42 tests) with mock-based testing
- CI pytest integration

## [0.1.3] - 2026-02-12

### Changed
- Updated PyPI package description

## [0.1.2] - 2026-02-12

### Changed
- Added introductory text and feature digest to README

## [0.1.1] - 2026-02-12

### Added
- `--headed` alias for `--no-headless`

### Fixed
- iNonius site name typo in documentation
- README language switch link to absolute URL

## [0.1.0] - 2026-02-12

### Added
- Initial release
- Automated speed testing on 8 sites (Cloudflare, Netflix, Google Fiber, Ookla, Box-test, M-Lab, USEN, iNonius)
- Zabbix trapper integration via zappix
- Probability-based frequency throttling per site
- Screenshot capture for debugging
- Headless/GUI Chrome mode
- CLI with `--dry-run`, site selection, and more
- systemd timer deployment files
- PyPI release workflow (TestPyPI + PyPI)

[0.3.0]: https://github.com/shigechika/speedtest-z/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/shigechika/speedtest-z/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/shigechika/speedtest-z/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/shigechika/speedtest-z/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/shigechika/speedtest-z/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/shigechika/speedtest-z/releases/tag/v0.1.0
