# Integrations

speedtest-z sends results to every enabled backend: Zabbix, Grafana Cloud, and any OTLP endpoint.

## Zabbix Integration

1. Import the `speedtest-z_templates.yaml` template into Zabbix.
2. All items are **trapper** type -- the agent pushes data to Zabbix using the zappix sender protocol.
3. Set `enable = true` in the `[zabbix]` section of `config.ini`.
4. The `host` value in `config.ini` must match the host name registered in Zabbix.

## Grafana Cloud Integration

![Grafana Dashboard](grafana.png)

speedtest-z can push metrics to Grafana Cloud via Prometheus Remote Write.

1. Install with Grafana support: `pip install speedtest-z[grafana]`
2. Add the `[grafana]` section to `config.ini`:

```ini
[grafana]
enable = true
remote_write_url = https://prometheus-prod-XX-prod-XX.grafana.net/api/prom/push
username = <your-prometheus-username>
token = <your-grafana-cloud-api-token>
```

3. Metrics are sent as `speedtest_<metric>` with a `site` label (e.g., `speedtest_download{site="cloudflare"}`).
4. Both Zabbix and Grafana can be enabled simultaneously -- results are sent to all enabled backends.

## OpenTelemetry (OTLP) Integration

speedtest-z can export metrics via OpenTelemetry Protocol (OTLP) to any OTLP-compatible backend.

1. Install with OTel support: `pip install speedtest-z[otel]`
2. Add the `[otel]` section to `config.ini`:

```ini
[otel]
enable = true
endpoint = https://otlp-gateway-prod-XX.grafana.net/otlp
headers = Authorization=Basic <base64-encoded-credentials>
```

3. Metrics are sent as `speedtest_<metric>` with `site` and `host` labels.
4. All three backends (Zabbix, Grafana, OTel) can be enabled simultaneously.

> **Note:** As of Feb 2026, direct OTLP metrics ingestion (without a collector) on **free tier** accounts is supported by very few backends. Grafana Cloud is the most mature option. Mackerel, GCP Cloud Monitoring, and AWS CloudWatch currently support OTLP traces only; Datadog requires an allowlisted organization. Paid plans may offer broader OTLP metrics support.
