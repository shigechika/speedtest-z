# 連携

speedtest-z は有効化した全バックエンド（Zabbix・Grafana Cloud・OTLP 対応バックエンド）へ結果を送信します。

## Zabbix連携

`speedtest-z_templates.yaml` を Zabbix にインポートすると、全テストサイトのアイテムが自動作成されます。

- 全アイテムはトラッパータイプ（`type: TRAP`）
- 速度系アイテムは Mbps → bps への前処理（MULTIPLIER x1000000）付き
- `config.ini` の `[zabbix]` セクションで `enable = true` に設定

## Grafana Cloud 連携

![Grafana ダッシュボード](grafana.png)

Prometheus Remote Write 経由で Grafana Cloud にメトリクスを送信できます。

1. Grafana 対応をインストール: `pip install speedtest-z[grafana]`
2. `config.ini` に `[grafana]` セクションを追加:

```ini
[grafana]
enable = true
remote_write_url = https://prometheus-prod-XX-prod-XX.grafana.net/api/prom/push
username = <Prometheus ユーザ名>
token = <Grafana Cloud API トークン>
```

3. メトリクスは `speedtest_<metric>{site="<site>"}` の形式で送信されます（例: `speedtest_download{site="cloudflare"}`）
4. Zabbix と Grafana は同時に有効化でき、計測結果は全ての有効なバックエンドに送信されます

```bash
# Zabbix Web UI → 設定 → テンプレート → インポート
# speedtest-z_templates.yaml を選択してインポート
```

## OpenTelemetry (OTLP) 連携

OpenTelemetry Protocol (OTLP) 経由で OTLP 対応バックエンドにメトリクスを送信できます。

1. OTel 対応をインストール: `pip install speedtest-z[otel]`
2. `config.ini` に `[otel]` セクションを追加:

```ini
[otel]
enable = true
endpoint = https://otlp-gateway-prod-XX.grafana.net/otlp
headers = Authorization=Basic <base64エンコード済み認証情報>
```

3. メトリクスは `speedtest_<metric>{site="<site>", host="<host>"}` の形式で送信されます
4. Zabbix、Grafana、OTel の3バックエンドを同時に有効化できます

> **注意:** 2026年2月時点で、**無料プラン**で Collector なしの OTLP メトリクス直接取り込みに対応しているバックエンドは限られています。Grafana Cloud が最も成熟した選択肢です。Mackerel・GCP Cloud Monitoring・AWS CloudWatch は現状 OTLP トレースのみ対応、Datadog は組織のホワイトリスト登録が必要です。有料プランではより広い OTLP メトリクス対応が期待できます。
