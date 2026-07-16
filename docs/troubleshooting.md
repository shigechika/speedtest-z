# Troubleshooting

| Problem | Solution |
|---------|----------|
| Tofu characters (□□□) in USEN/iNonius snapshots on Linux | Install Japanese fonts: `sudo apt install fonts-noto-cjk` |
| ChromeDriver version mismatch error | Selenium Manager auto-downloads the matching driver. Update `selenium` package: `pip install -U selenium` |
| Site test hangs or times out | Increase timeout: `speedtest-z --timeout 60` or check your network |
| `config.ini` not found | Place it in one of: `./`, `~/.config/speedtest-z/`, or `/etc/speedtest-z/`. Copy from `config.ini-sample` |
| Zabbix sender connection refused | Verify `server` and `port` in `[zabbix]` section, ensure zabbix_sender is reachable |
| Grafana Cloud 401/403 | Check `token` scope (needs `MetricsPublisher` role) in `[grafana]` section |
| `ModuleNotFoundError: cramjam` | Install with Grafana support: `pip install speedtest-z[grafana]` |
| `ModuleNotFoundError: opentelemetry` | Install with OTel support: `pip install speedtest-z[otel]` |
