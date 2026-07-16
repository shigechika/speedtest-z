# 設定ファイル

## config.ini

設定ファイルは以下の順序で探索されます（`-c` / `--config` で明示指定も可能）：

1. CLI で指定されたパス（`-c` / `--config`）
2. カレントディレクトリの `./config.ini`
3. `~/.config/speedtest-z/config.ini`（XDG_CONFIG_HOME）
4. `/etc/speedtest-z/config.ini`（システム全体、`.deb` パッケージで使用）

`config.ini-sample` をコピーして編集してください。

### `[general]` セクション

```ini
[general]
# 実行モード設定
dry_run = true          # true にすると外部送信しない（旧名 dryrun も互換サポート）
headless = false        # ヘッドレスモード（GUI なし）
timeout = 30            # 各テストのタイムアウト（秒）
# ookla_server = IPA CyberLab 400G   # Ookla テストサーバ（省略時: 自動選択）
```

### `[zabbix]` セクション

```ini
[zabbix]
enable = false           # true にすると Zabbix へ送信する
server = 127.0.0.1       # 送信先 Zabbix Server
port = 10051             # Zabbix トラッパーポート
host = speedtest-agent   # Zabbix ホスト名
# 任意: バージョンを host tag（speedtest-z=<version>）として Zabbix API 経由で付与。
# speedtest-z[zabbix-api] が必要。api_url/api_user/api_password の3つすべて設定すると有効。
# api_url = https://zabbix.example.com/api_jsonrpc.php
# api_user = api-user
# api_password = api-pass
```

### `[grafana]` セクション（オプション）

```ini
[grafana]
enable = false
remote_write_url = https://prometheus-prod-XX-prod-XX.grafana.net/api/prom/push
username = <Prometheus ユーザ名>
token = <Grafana Cloud API トークン>
```

### `[otel]` セクション（オプション）

```ini
[otel]
enable = false
endpoint = https://otlp-gateway-prod-XX.grafana.net/otlp
# カンマ区切りの Key=Value ペア（OTEL_EXPORTER_OTLP_HEADERS と同じ形式）
headers = Authorization=Basic <base64エンコード済み認証情報>
```

### `[snapshot]` セクション

```ini
[snapshot]
enable = true            # 画面キャプチャの有効/無効
save_dir = ./snapshots   # スクリーンショット保存先
```

### `[frequency]` セクション

各サイトの実行確率を 0〜100 で設定します。0 で無効化、100 で毎回実行、50 で約半分の確率で実行されます。

```ini
[frequency]
cloudflare = 100
netflix = 100
google = 100
ookla = 50
boxtest = 50
mlab = 10
usen = 50
inonius = 50
```

## logging.ini

`config.ini` と同じ探索順で検索されます（任意）：

1. カレントディレクトリの `./logging.ini`
2. `~/.config/speedtest-z/logging.ini`（XDG_CONFIG_HOME）
3. `/etc/speedtest-z/logging.ini`（システム全体）

いずれも見つからない場合は、デフォルトのログ設定（INFO レベル、stdout 出力）が使用されます。
