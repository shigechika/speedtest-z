# Installation

## Prerequisites

- Python >= 3.10
- Google Chrome browser (not installable via pip -- must be installed separately)

## Homebrew (macOS)

```bash
brew install shigechika/tap/speedtest-z
```

Pre-built bottles are available for macOS Sonoma (14) and Sequoia (15) on Apple Silicon. Installation completes in seconds.

## Debian / Ubuntu (.deb)

Download the `.deb` package for your distribution from [GitHub Releases](https://github.com/shigechika/speedtest-z/releases):

```bash
# Ubuntu 24.04 (Noble)
sudo dpkg -i speedtest-z_*~noble.deb

# Ubuntu 22.04 (Jammy)
sudo dpkg -i speedtest-z_*~jammy.deb
```

The `.deb` package includes all Python dependencies in a self-contained virtualenv (`/opt/venvs/speedtest-z/`), systemd service/timer (installed disabled), and config files in `/etc/speedtest-z/`.

```bash
# Edit config
sudo vi /etc/speedtest-z/config.ini

# Enable scheduled execution (every 10 minutes)
sudo systemctl enable --now speedtest-z.timer
```

## RHEL / Rocky Linux / AlmaLinux (.rpm)

Download the `.rpm` package from [GitHub Releases](https://github.com/shigechika/speedtest-z/releases):

```bash
# RHEL 9 / Rocky Linux 9 / AlmaLinux 9
sudo dnf install python3.11
sudo rpm -ivh speedtest-z-*-1.el9.x86_64.rpm
```

The `.rpm` package has the same structure as the `.deb` package: self-contained virtualenv in `/opt/venvs/speedtest-z/`, systemd service/timer, and config files in `/etc/speedtest-z/`.

## pip / uv

```bash
pip install speedtest-z

# or using uv
uv tool install speedtest-z
```

## Development Setup

```bash
git clone https://github.com/shigechika/speedtest-z.git
cd speedtest-z
python3 -m venv .venv
. .venv/bin/activate
pip install -e .

# or using uv
uv sync
```

## Dependencies

- [selenium](https://pypi.org/project/selenium/) -- Browser automation
- [zappix](https://pypi.org/project/zappix/) -- Zabbix sender protocol

## Grafana Cloud Support (optional)

```bash
pip install speedtest-z[grafana]

# or using uv
uv tool install "speedtest-z[grafana]"
```

This installs `cramjam` for Snappy compression required by Prometheus Remote Write.

## OpenTelemetry Support (optional)

```bash
pip install speedtest-z[otel]

# or using uv
uv tool install "speedtest-z[otel]"
```

This installs the OpenTelemetry SDK and OTLP HTTP exporter for sending metrics via OTLP.

## Zabbix Host Version Tag (optional)

```bash
pip install speedtest-z[zabbix-api]

# or using uv
uv tool install "speedtest-z[zabbix-api]"
```

This installs [zapi-lib](https://github.com/shigechika/zapi-lib) so speedtest-z can stamp its running version onto the Zabbix host as a tag (`speedtest-z=<version>`) via the Zabbix JSON-RPC API, alongside the trapper send path. Set `api_url` / `api_user` / `api_password` under `[zabbix]` to enable it. Use an `https` `api_url`, keep `config.ini` readable only by its owner (the password is stored in plaintext), and prefer a least-privilege Zabbix API user (`host.update` only).

## Tab Completion (optional)

```bash
pip install speedtest-z[completion]
eval "$(register-python-argcomplete speedtest-z)"
```

Add the `eval` line to your shell profile (`~/.bashrc` or `~/.zshrc`) to enable it permanently.
