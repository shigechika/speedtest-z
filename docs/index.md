# speedtest-z

speedtest-z automates major speed test sites with a web browser, capturing real user-experience network quality for continuous monitoring.

- Supports 8 speed test sites (Cloudflare, Netflix, Ookla, M-Lab, and more)
- Zabbix integration for continuous network quality monitoring
- Quick start: `pip install speedtest-z`

![Demo - 8 speed test sites](demo.gif)

See [Installation](install.md) to get started, and [Usage](usage.md) for the CLI.

## Features

- Runs speed tests on 8 different sites automatically (Cloudflare, Netflix/fast.com, Google Fiber, Ookla, Box-test, M-Lab, USEN, iNonius)
- Sends results to Zabbix via trapper items (using [zappix](https://pypi.org/project/zappix/))
- Optional Grafana Cloud integration via Prometheus Remote Write
- Optional OpenTelemetry (OTLP) metrics export
- Configurable test frequency per site (probability-based throttling)
- Screenshot capture for debugging
- Headless or GUI Chrome mode
- CLI with `--dry-run`, site selection, etc.
- systemd timer integration for scheduled execution

## Share Your Results!

Got the fastest or slowest speed test result? We'd love to see it!

Submit your results via [GitHub Issues](https://github.com/shigechika/speedtest-z/issues/new?template=speedtest-result.yml) with:
- Screenshot(s) from the `snapshots/` directory
- CLI log output (`speedtest-z --dry-run`)

Whether it's blazing fast datacenter fiber or painfully slow hotel Wi-Fi, all results are welcome.

## License

[Apache License 2.0](https://github.com/shigechika/speedtest-z/blob/main/LICENSE)

Copyright 2026 AIKAWA Shigechika
