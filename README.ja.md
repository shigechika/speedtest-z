# speedtest-z

[![PyPI version](https://img.shields.io/pypi/v/speedtest-z)](https://pypi.org/project/speedtest-z/)
[![CI](https://github.com/shigechika/speedtest-z/actions/workflows/ci.yml/badge.svg)](https://github.com/shigechika/speedtest-z/actions/workflows/ci.yml)
[![Python](https://img.shields.io/pypi/pyversions/speedtest-z)](https://pypi.org/project/speedtest-z/)

[English](https://github.com/shigechika/speedtest-z/blob/main/README.md) | [ドキュメント](https://shigechika.github.io/speedtest-z/ja/)

speedtest-z は Web ブラウザで主要な速度テストサイトを自動巡回。ユーザ体験そのままの回線品質を定点観測できます。

- 8つの速度テストサイトに対応（Cloudflare, Netflix, Ookla, M-Lab 等）
- Zabbix 連携で回線品質を継続監視
- `pip install speedtest-z` ですぐ使える

![デモ - 8サイト速度テスト結果](docs/demo.gif)

## 特徴

- 8つの速度テストサイトを自動実行（Cloudflare, Netflix/fast.com, Google Fiber, Ookla, Box-test, M-Lab, USEN, iNonius）
- Zabbixへトラッパーアイテムとして結果送信（[zappix](https://pypi.org/project/zappix/) 使用）
- Grafana Cloud 連携（Prometheus Remote Write、オプション）
- OpenTelemetry (OTLP) メトリクス送信（オプション）
- サイトごとの実行頻度設定（確率ベースのスロットリング）
- デバッグ用スクリーンショット保存
- ヘッドレス/GUI Chromeモード切替
- CLI対応（`--dry-run`、サイト指定等）
- systemd timerによるスケジュール実行

## 前提条件

- Python >= 3.10
- Google Chrome ブラウザ（pip ではインストールされません）

## インストール

### Homebrew (macOS)

```bash
brew install shigechika/tap/speedtest-z
```

macOS Sonoma (14) / Sequoia (15) の Apple Silicon 向けにビルド済み bottle が提供されており、数秒でインストールが完了します。

### Debian / Ubuntu (.deb)

[GitHub Releases](https://github.com/shigechika/speedtest-z/releases) からディストリビューションに合った `.deb` パッケージをダウンロード:

```bash
# Ubuntu 24.04 (Noble)
sudo dpkg -i speedtest-z_*~noble.deb

# Ubuntu 22.04 (Jammy)
sudo dpkg -i speedtest-z_*~jammy.deb
```

`.deb` パッケージは Python 依存をすべて含む自己完結型 virtualenv（`/opt/venvs/speedtest-z/`）、systemd service/timer（無効状態でインストール）、設定ファイル（`/etc/speedtest-z/`）を含みます。

```bash
# 設定を編集
sudo vi /etc/speedtest-z/config.ini

# スケジュール実行を有効化（10分間隔）
sudo systemctl enable --now speedtest-z.timer
```

### RHEL / Rocky Linux / AlmaLinux (.rpm)

[GitHub Releases](https://github.com/shigechika/speedtest-z/releases) から `.rpm` パッケージをダウンロード:

```bash
# RHEL 9 / Rocky Linux 9 / AlmaLinux 9
sudo dnf install python3.11
sudo rpm -ivh speedtest-z-*-1.el9.x86_64.rpm
```

`.rpm` パッケージは `.deb` と同様の構成です: `/opt/venvs/speedtest-z/` に自己完結型 virtualenv、systemd service/timer、設定ファイル（`/etc/speedtest-z/`）を含みます。

### pip / uv

```bash
pip install speedtest-z

# uv を使う場合
uv tool install speedtest-z
```

### 開発用インストール

```bash
git clone https://github.com/shigechika/speedtest-z.git
cd speedtest-z
python3 -m venv .venv
. .venv/bin/activate
pip install -e .

# uv を使う場合
uv sync
```

### 依存ライブラリ

- [selenium](https://pypi.org/project/selenium/) — ブラウザ自動操作
- [zappix](https://pypi.org/project/zappix/) — Zabbix トラッパー送信

### Grafana Cloud 対応（オプション）

```bash
pip install speedtest-z[grafana]

# uv を使う場合
uv tool install "speedtest-z[grafana]"
```

Prometheus Remote Write に必要な Snappy 圧縮ライブラリ `cramjam` がインストールされます。

### OpenTelemetry 対応（オプション）

```bash
pip install speedtest-z[otel]

# uv を使う場合
uv tool install "speedtest-z[otel]"
```

OpenTelemetry SDK と OTLP HTTP エクスポーターがインストールされます。

### Zabbix ホストバージョンタグ（オプション）

```bash
pip install speedtest-z[zabbix-api]

# uv を使う場合
uv tool install "speedtest-z[zabbix-api]"
```

[zapi-lib](https://github.com/shigechika/zapi-lib) がインストールされ、トラッパー送信に加えて、実行中の speedtest-z バージョンを Zabbix API 経由で host tag（`speedtest-z=<version>`）として付与できます。`[zabbix]` セクションの `api_url` / `api_user` / `api_password` を設定すると有効になります。`api_url` は https を推奨し、`config.ini` は所有者のみ読めるよう権限を制限してください（パスワードは平文で保存されます）。Zabbix API ユーザーは最小権限（`host.update` のみ）を推奨します。

### タブ補完（任意）

```bash
pip install speedtest-z[completion]
eval "$(register-python-argcomplete speedtest-z)"
```

`eval` の行を `~/.bashrc` や `~/.zshrc` に追記すると常時有効になります。

## 設定ファイル

### config.ini

設定ファイルは以下の順序で探索されます（`-c` / `--config` で明示指定も可能）：

1. CLI で指定されたパス（`-c` / `--config`。指定したファイルが存在しない場合、他の場所へのフォールバックは行われません）
2. カレントディレクトリの `./config.ini`
3. `~/.config/speedtest-z/config.ini`（XDG_CONFIG_HOME）
4. `/etc/speedtest-z/config.ini`（システム全体、`.deb` パッケージで使用）

`config.ini-sample` をコピーして編集してください。

#### `[general]` セクション

```ini
[general]
# 実行モード設定
dry_run = true          # true にすると外部送信しない（旧名 dryrun も互換サポート）
headless = false        # ヘッドレスモード（GUI なし）
timeout = 30            # 各テストのタイムアウト（秒）
# ookla_server = IPA CyberLab 400G   # Ookla テストサーバ（省略時: 自動選択）
```

#### `[zabbix]` セクション

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

#### `[grafana]` セクション（オプション）

```ini
[grafana]
enable = false
remote_write_url = https://prometheus-prod-XX-prod-XX.grafana.net/api/prom/push
username = <Prometheus ユーザ名>
token = <Grafana Cloud API トークン>
```

#### `[otel]` セクション（オプション）

```ini
[otel]
enable = false
endpoint = https://otlp-gateway-prod-XX.grafana.net/otlp
# カンマ区切りの Key=Value ペア（OTEL_EXPORTER_OTLP_HEADERS と同じ形式）
headers = Authorization=Basic <base64エンコード済み認証情報>
```

#### `[snapshot]` セクション

```ini
[snapshot]
enable = true            # 画面キャプチャの有効/無効
save_dir = ./snapshots   # スクリーンショット保存先
```

#### `[frequency]` セクション

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

### logging.ini

`config.ini` と同じ探索順で検索されます（任意）：

1. カレントディレクトリの `./logging.ini`
2. `~/.config/speedtest-z/logging.ini`（XDG_CONFIG_HOME）
3. `/etc/speedtest-z/logging.ini`（システム全体）

いずれも見つからない場合は、デフォルトのログ設定（INFO レベル、stdout 出力）が使用されます。

## 使い方

```
speedtest-z [options] [site ...]
```

### CLIオプション

| オプション | 説明 |
|-----------|------|
| `-V`, `--version` | バージョン表示 |
| `-m`, `--man` | マニュアル（README）をページャで表示して終了 |
| `-c`, `--config CONFIG` | 設定ファイル指定 |
| `-n`, `--dry-run` | テスト実行（Zabbix へ送信しない） |
| `--headless` | ヘッドレスモードで実行 |
| `--no-headless`, `--headed` | GUI モードで実行 |
| `--timeout SECONDS` | 各テストのタイムアウト（秒） |
| `--list-sites` | 利用可能なテストサイト一覧を表示して終了 |
| `--check` | テストサイト URL の疎通確認を行い終了（Chrome 不要） |
| `-o`, `--output FORMAT` | 出力形式: `zabbix`（デフォルト）、`json`、`csv` |
| `-d`, `--debug` | デバッグ出力を有効化 |
| `site` | 実行するテストサイト（位置引数、省略時は全サイト） |

### 確認プロンプト

対話的なターミナル（TTY）から実行すると、テストサイトへの接続前に確認を求めます。cron や systemd、パイプ経由など非対話環境では自動的にスキップされます。

```
$ speedtest-z -n
speedtest-z: 8 サイトに接続します (cloudflare, netflix, ...)
続行しますか？ [y/N]: y
```

### 実行例

```bash
# 全サイトをテスト実行（Zabbix に送信しない）
speedtest-z -n

# 特定サイトのみ実行
speedtest-z cloudflare netflix

# GUI モードでデバッグ実行
speedtest-z --no-headless -d google

# 利用可能なサイト一覧を表示
speedtest-z --list-sites

# テストサイト URL の疎通確認（Chrome 不要）
speedtest-z --check

# 特定サイトのみ疎通確認
speedtest-z --check cloudflare netflix

# 結果を JSON で出力（Zabbix 送信はスキップ）
speedtest-z --dry-run --output json cloudflare 2>/dev/null

# 結果を CSV で出力
speedtest-z --dry-run -o csv cloudflare netflix 2>/dev/null
```

## 実行例

```
$ speedtest-z --dry-run
speedtest-z: 8 サイトに接続します (cloudflare, netflix, google, ookla, boxtest, mlab, usen, inonius)
続行しますか？ [y/N]: y
2026-02-25 15:00:01 [INFO] speedtest-z: START
2026-02-25 15:00:01 [INFO] Config loaded: config.ini
2026-02-25 15:00:01 [INFO] Initializing Chrome WebDriver...
2026-02-25 15:00:02 [INFO] cloudflare: OPEN
2026-02-25 15:00:09 [INFO] cloudflare: Test started
2026-02-25 15:00:58 [INFO] cloudflare: COMPLETED (Quality Scores appeared)
2026-02-25 15:00:58 [INFO] netflix: OPEN
2026-02-25 15:01:24 [INFO] netflix: COMPLETED (succeeded class detected)
2026-02-25 15:01:24 [INFO] google: OPEN
2026-02-25 15:01:51 [INFO] google: COMPLETED
2026-02-25 15:01:51 [INFO] ookla: OPEN (Attempt 1/3)
2026-02-25 15:02:31 [INFO] ookla: COMPLETED
2026-02-25 15:02:33 [INFO] boxtest: OPEN
2026-02-25 15:03:48 [INFO] boxtest: COMPLETED
2026-02-25 15:03:48 [INFO] mlab: OPEN
2026-02-25 15:04:36 [INFO] mlab: COMPLETED
2026-02-25 15:04:36 [INFO] usen: OPEN
2026-02-25 15:05:05 [INFO] usen: COMPLETED (speedtest_wait class removed)
2026-02-25 15:05:05 [INFO] inonius: OPEN
2026-02-25 15:06:02 [INFO] inonius: COMPLETED
2026-02-25 15:06:02 [INFO] speedtest-z: FINISH
```

全8サイトの計測が約6分で完了しています。

## 対応テストサイト

| サイト名 | URL | 取得メトリクス |
|----------|-----|---------------|
| `cloudflare` | https://speed.cloudflare.com/ | download, upload, latency, jitter |
| `netflix` | https://fast.com/ | download, upload, latency, server-locations |
| `google` | http://speed.googlefiber.net/ | download, upload, ping |
| `ookla` | https://www.speedtest.net/ | download, upload, ping |
| `boxtest` | https://www.box-test.com/ | POP, DownloadSpeed, DownloadDuration, DownloadRTT, UploadSpeed, UploadDuration, UploadRTT, latency |
| `mlab` | https://speed.measurementlab.net/ | download, upload, latency, retrans |
| `usen` | https://speedtest.gate02.ne.jp/ | download, upload, ping, jitter |
| `inonius` | https://inonius.net/speedtest/ | IPv4/IPv6 各: DL, UL, RTT, JIT, MSS |

> **注意: Google Fiber (speed.googlefiber.net) とジャンボフレーム**
>
> speed.googlefiber.net は HTTPS 非対応（HTTP のみ）で、AAAA レコードを持ちません。IPv6-only 環境では DNS64/NAT64 経由でアクセスしますが、**NIC の MTU が 9000（ジャンボフレーム）の場合、ページの JavaScript が読み込めず画面が真っ白になります**。MTU を 1500 に設定してください。

## Zabbix連携

`speedtest-z_templates.yaml` を Zabbix にインポートすると、全テストサイトのアイテムが自動作成されます。

- 全アイテムはトラッパータイプ（`type: TRAP`）
- 速度系アイテムは Mbps → bps への前処理（MULTIPLIER x1000000）付き
- `config.ini` の `[zabbix]` セクションで `enable = true` に設定

## Grafana Cloud 連携

![Grafana ダッシュボード](docs/grafana.png)

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

## デプロイ（systemd）

> **Note:** `.deb` / `.rpm` パッケージには systemd service/timer が同梱されています。インストール後 `sudo systemctl enable --now speedtest-z.timer` で有効化するだけです。

pip でインストールした場合は、`deploy/` ディレクトリに systemd のサービスファイルとタイマーファイルが含まれています。

```bash
# サービスファイルとタイマーファイルをコピー
sudo cp deploy/speedtest-z.service /etc/systemd/system/
sudo cp deploy/speedtest-z.timer /etc/systemd/system/

# 必要に応じてサービスファイルの ExecStart パスを編集
sudo systemctl daemon-reload

# タイマーを有効化・起動（10分間隔で実行）
sudo systemctl enable --now speedtest-z.timer

# 動作確認
systemctl status speedtest-z.timer
systemctl list-timers speedtest-z.timer
```

### Selenium クリーナー（cron）

Chrome の一時ファイルを定期的に削除する cron 設定も含まれています。

```bash
sudo cp deploy/SeleniumCleaner.cron /etc/cron.d/SeleniumCleaner
```

## 計測結果を共有しませんか？

爆速回線や激遅 Wi-Fi の計測結果をお待ちしています！

[GitHub Issues](https://github.com/shigechika/speedtest-z/issues/new?template=speedtest-result.yml) から以下を添えて投稿してください:
- `snapshots/` ディレクトリのスクリーンショット
- CLI ログ出力（`speedtest-z --dry-run`）

データセンターの超高速回線でも、山小屋の激遅 Wi-Fi でも大歓迎です。

## トラブルシューティング

| 問題 | 解決策 |
|------|--------|
| Linux で USEN/iNonius のスナップショットが豆腐文字（□□□）になる | 日本語フォントをインストール: `sudo apt install fonts-noto-cjk` |
| ChromeDriver のバージョン不一致エラー | Selenium Manager が自動でダウンロードします。`selenium` パッケージを更新: `pip install -U selenium` |
| テストがハングする・タイムアウトする | タイムアウトを延長: `speedtest-z --timeout 60`、またはネットワーク接続を確認 |
| `config.ini` が見つからない | `./`、`~/.config/speedtest-z/`、`/etc/speedtest-z/` のいずれかに配置。`config.ini-sample` からコピー |
| Zabbix sender の接続が拒否される | `[zabbix]` セクションの `server` と `port` を確認、zabbix_sender への疎通を確認 |
| Grafana Cloud で 401/403 エラー | `[grafana]` セクションの `token` のスコープを確認（`MetricsPublisher` ロールが必要） |
| `ModuleNotFoundError: cramjam` | Grafana 対応をインストール: `pip install speedtest-z[grafana]` |
| `ModuleNotFoundError: opentelemetry` | OTel 対応をインストール: `pip install speedtest-z[otel]` |

## License

[Apache License 2.0](LICENSE)

Copyright 2026 AIKAWA Shigechika
