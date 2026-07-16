# Configuration

## config.ini

The configuration file is searched in the following order (`-c` / `--config` can override):

1. `./config.ini` in the current directory
2. `~/.config/speedtest-z/config.ini` (XDG_CONFIG_HOME)
3. `/etc/speedtest-z/config.ini` (system-wide, used by `.deb` package)

Copy `config.ini-sample` to one of these locations and edit as needed.

### Sections

```ini
[general]
# Run mode
dry_run = true         # true = do not send data to backends
headless = false       # true = run Chrome in headless mode
timeout = 30           # timeout in seconds for each test
# ookla_server = IPA CyberLab 400G   # Ookla test server (omit for auto-select)

[zabbix]
# Zabbix server settings
enable = false           # true = send results to Zabbix
server = 127.0.0.1
port = 10051
host = speedtest-agent   # Zabbix host name for trapper items
# Optional: stamp the version as a host tag (speedtest-z=<version>) via the
# Zabbix API. Requires speedtest-z[zabbix-api]; all three must be set.
# api_url = https://zabbix.example.com/api_jsonrpc.php
# api_user = api-user
# api_password = api-pass

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

# [grafana]
# # Grafana Cloud Prometheus Remote Write
# enable = false
# remote_write_url = https://prometheus-prod-XX-prod-XX.grafana.net/api/prom/push
# username =
# token =

# [otel]
# # OpenTelemetry (OTLP) metrics export
# enable = false
# endpoint = https://otlp-gateway-prod-XX.grafana.net/otlp
# # Comma-separated Key=Value pairs (same format as OTEL_EXPORTER_OTLP_HEADERS)
# headers = Authorization=Basic <base64-encoded-credentials>
```

> **Note:** The `dryrun` key (without underscore) is still supported for backward compatibility but `dry_run` is preferred.

## logging.ini

An optional `logging.ini` file can be used to customize log output. The file is searched in the same order as `config.ini`:

1. `./logging.ini` in the current directory
2. `~/.config/speedtest-z/logging.ini` (XDG_CONFIG_HOME)
3. `/etc/speedtest-z/logging.ini` (system-wide)

If none is found, the default logging configuration (INFO level to stdout) is used.
