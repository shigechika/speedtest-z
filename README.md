# speedtest-z

[日本語](README.ja.md)

An automated multi-site speed test runner using Selenium, with Zabbix trapper integration.

![Demo - 8 speed test sites](docs/demo.gif)

## Features

- Runs speed tests on 8 different sites automatically (Cloudflare, Netflix/fast.com, Google Fiber, Ookla, Box-test, M-Lab, USEN, inonius)
- Sends results to Zabbix via trapper items (using [zappix](https://pypi.org/project/zappix/))
- Configurable test frequency per site (probability-based throttling)
- Screenshot capture for debugging
- Headless or GUI Chrome mode
- CLI with `--dry-run`, site selection, etc.
- systemd timer integration for scheduled execution

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Supported Test Sites](#supported-test-sites)
- [Zabbix Integration](#zabbix-integration)
- [Deployment (systemd)](#deployment-systemd)
- [License](#license)

## Prerequisites

- Python >= 3.10
- Google Chrome browser (not installable via pip -- must be installed separately)

## Installation

```bash
pip install speedtest-z
```

### Development Setup

```bash
git clone https://github.com/shigechika/speedtest-z.git
cd speedtest-z
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

### Dependencies

- [selenium](https://pypi.org/project/selenium/) -- Browser automation
- [zappix](https://pypi.org/project/zappix/) -- Zabbix sender protocol

## Configuration

### config.ini

The configuration file is searched in the following order (`-c` / `--config` can override):

1. `./config.ini` in the current directory
2. `~/.config/speedtest-z/config.ini` (XDG_CONFIG_HOME)

Copy `config.ini-sample` to one of these locations and edit as needed.

#### Sections

```ini
[general]
# Execution mode
dryrun = true          # true = do not send data to Zabbix
headless = true        # true = run Chrome in headless mode
timeout = 30           # timeout in seconds for each test
# ookla_server = IPA CyberLab   # Ookla test server (omit for auto-select)

[zabbix]
# Zabbix server settings
server = 127.0.0.1
port = 10051
host = speedtest-agent   # Zabbix host name for trapper items

[snapshot]
# Screenshot capture settings
enable = true
save_dir = ./snapshots

[frequency]
# Execution probability per site (0-100)
# 100 = always run, 50 = ~50% chance, 0 = disabled
cloudflare = 100
netflix = 100
google = 100
ookla = 50
boxtest = 50
mlab = 10
usen = 50
inonius = 50
```

### logging.ini

An optional `logging.ini` file can be used to customize log output. The file is searched in the same order as `config.ini`:

1. `./logging.ini` in the current directory
2. `~/.config/speedtest-z/logging.ini` (XDG_CONFIG_HOME)

If neither is found, the default logging configuration (INFO level to stdout) is used.

## Usage

```
speedtest-z [options] [site ...]
```

### Options

| Option | Description |
|--------|-------------|
| `-V`, `--version` | Show program version and exit |
| `-c`, `--config CONFIG` | Config file path (default: `./config.ini` or `~/.config/speedtest-z/config.ini`) |
| `-n`, `--dry-run` | Test run (do not send data to Zabbix) |
| `--headless` | Run Chrome in headless mode |
| `--no-headless`, `--headed` | Run Chrome with GUI (non-headless) |
| `--timeout SECONDS` | Timeout in seconds for each test |
| `--list-sites` | List available test sites and exit |
| `-d`, `--debug` | Enable debug output |
| `site` | Positional argument(s): test site(s) to run (default: all) |

### Examples

```bash
# Run all test sites (dry-run)
speedtest-z -n

# Run specific sites
speedtest-z cloudflare netflix

# Run with GUI browser for debugging
speedtest-z --no-headless -d cloudflare

# List available sites
speedtest-z --list-sites
```

## Example Output

Measured at JANOG57 Meeting (Feb 2026, Osaka):

```
$ speedtest-z --dry-run
2026-02-13 09:39:27 [INFO] speedtest-z: START
2026-02-13 09:39:27 [INFO] Config loaded: config.ini
2026-02-13 09:39:27 [INFO] Initializing Chrome WebDriver...
2026-02-13 09:39:28 [INFO] cloudflare: OPEN
2026-02-13 09:39:35 [INFO] cloudflare: Test started
2026-02-13 09:40:24 [INFO] cloudflare: COMPLETED (Quality Scores appeared)
2026-02-13 09:40:27 [INFO] Dryrun: True - Data not sent.
2026-02-13 09:40:27 [INFO] netflix: OPEN
2026-02-13 09:40:53 [INFO] netflix: COMPLETED (succeeded class detected)
2026-02-13 09:40:53 [INFO] google: OPEN
2026-02-13 09:41:20 [INFO] google: COMPLETED
2026-02-13 09:41:20 [INFO] ookla: OPEN (Attempt 1/3)
2026-02-13 09:42:00 [INFO] ookla: COMPLETED
2026-02-13 09:42:02 [INFO] boxtest: OPEN
2026-02-13 09:43:17 [INFO] boxtest: COMPLETED
2026-02-13 09:43:17 [INFO] mlab: OPEN
2026-02-13 09:44:05 [INFO] mlab: COMPLETED
2026-02-13 09:44:05 [INFO] usen: OPEN
2026-02-13 09:44:34 [INFO] usen: COMPLETED (speedtest_wait class removed)
2026-02-13 09:44:34 [INFO] inonius: OPEN
2026-02-13 09:45:31 [INFO] inonius: COMPLETED
2026-02-13 09:45:31 [INFO] speedtest-z: FINISH
```

All 8 sites completed in about 6 minutes.

## Supported Test Sites

| Site | URL | Metrics (Zabbix keys) |
|------|-----|----------------------|
| `cloudflare` | https://speed.cloudflare.com/ | download, upload, latency, jitter |
| `netflix` | https://fast.com/ | download, upload, latency, server-locations |
| `google` | https://speed.googlefiber.net/ | download, upload, ping |
| `ookla` | https://www.speedtest.net/ | download, upload, ping |
| `boxtest` | https://www.box-test.com/ | POP, DownloadSpeed, DownloadDuration, DownloadRTT, UploadSpeed, UploadDuration, UploadRTT, latency |
| `mlab` | https://speed.measurementlab.net/ | download, upload, latency, retrans |
| `usen` | https://speedtest.gate02.ne.jp/ | download, upload, ping, jitter |
| `inonius` | https://inonius.net/speedtest/ | IPv4/IPv6: DL, UL, RTT, JIT, MSS |

All Zabbix item keys are prefixed with the site name (e.g., `cloudflare.download`, `usen.ping`, `inonius.IPv4_DL`).

## Zabbix Integration

1. Import the `speedtest-z_templates.yaml` template into Zabbix.
2. All items are **trapper** type -- the agent pushes data to Zabbix using the zappix sender protocol.
3. Set the `[zabbix]` section in `config.ini` to match your Zabbix server settings.
4. The `host` value in `config.ini` must match the host name registered in Zabbix.

## Deployment (systemd)

The `deploy/` directory contains systemd unit files for scheduled execution:

| File | Description |
|------|-------------|
| `speedtest-z.service` | Service unit (runs `speedtest-z` from the venv) |
| `speedtest-z.timer` | Timer unit (runs every 6 minutes) |
| `SeleniumCleaner.cron` | Cron job to clean up stale Chrome temp files |

### Setup

```bash
# Copy unit files
cp deploy/speedtest-z.service ~/.config/systemd/user/
cp deploy/speedtest-z.timer ~/.config/systemd/user/

# Reload and enable
systemctl --user daemon-reload
systemctl --user enable --now speedtest-z.timer

# Check status
systemctl --user status speedtest-z.timer
systemctl --user list-timers
```

Optionally, install the cron job for cleaning up stale Chrome temporary directories:

```bash
sudo cp deploy/SeleniumCleaner.cron /etc/cron.d/SeleniumCleaner
```

## Share Your Results!

Got the fastest or slowest speed test result? We'd love to see it!

Submit your results via [GitHub Issues](https://github.com/shigechika/speedtest-z/issues/new?template=speedtest-result.yml) with:
- Screenshot(s) from the `snapshots/` directory
- CLI log output (`speedtest-z --dry-run`)

Whether it's blazing fast datacenter fiber or painfully slow hotel Wi-Fi, all results are welcome.

## License

[Apache License 2.0](LICENSE)

Copyright 2026 AIKAWA Shigechika
