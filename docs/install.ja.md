# インストール

## 前提条件

- Python >= 3.10
- Google Chrome ブラウザ（pip ではインストールされません）

## Homebrew (macOS)

```bash
brew install shigechika/tap/speedtest-z
```

macOS Sonoma (14) / Sequoia (15) の Apple Silicon 向けにビルド済み bottle が提供されており、数秒でインストールが完了します。

## Debian / Ubuntu (.deb)

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

## RHEL / Rocky Linux / AlmaLinux (.rpm)

[GitHub Releases](https://github.com/shigechika/speedtest-z/releases) から `.rpm` パッケージをダウンロード:

```bash
# RHEL 9 / Rocky Linux 9 / AlmaLinux 9
sudo dnf install python3.11
sudo rpm -ivh speedtest-z-*-1.el9.x86_64.rpm
```

`.rpm` パッケージは `.deb` と同様の構成です: `/opt/venvs/speedtest-z/` に自己完結型 virtualenv、systemd service/timer、設定ファイル（`/etc/speedtest-z/`）を含みます。

## pip / uv

```bash
pip install speedtest-z

# uv を使う場合
uv tool install speedtest-z
```

## 開発用インストール

```bash
git clone https://github.com/shigechika/speedtest-z.git
cd speedtest-z
python3 -m venv .venv
. .venv/bin/activate
pip install -e .

# uv を使う場合
uv sync
```

## 依存ライブラリ

- [selenium](https://pypi.org/project/selenium/) — ブラウザ自動操作
- [zappix](https://pypi.org/project/zappix/) — Zabbix トラッパー送信

## Grafana Cloud 対応（オプション）

```bash
pip install speedtest-z[grafana]

# uv を使う場合
uv tool install "speedtest-z[grafana]"
```

Prometheus Remote Write に必要な Snappy 圧縮ライブラリ `cramjam` がインストールされます。

## OpenTelemetry 対応（オプション）

```bash
pip install speedtest-z[otel]

# uv を使う場合
uv tool install "speedtest-z[otel]"
```

OpenTelemetry SDK と OTLP HTTP エクスポーターがインストールされます。

## Zabbix ホストバージョンタグ（オプション）

```bash
pip install speedtest-z[zabbix-api]

# uv を使う場合
uv tool install "speedtest-z[zabbix-api]"
```

[zapi-lib](https://github.com/shigechika/zapi-lib) がインストールされ、トラッパー送信に加えて、実行中の speedtest-z バージョンを Zabbix API 経由で host tag（`speedtest-z=<version>`）として付与できます。`[zabbix]` セクションの `api_url` / `api_user` / `api_password` を設定すると有効になります。`api_url` は https を推奨し、`config.ini` は所有者のみ読めるよう権限を制限してください（パスワードは平文で保存されます）。Zabbix API ユーザーは最小権限（`host.update` のみ）を推奨します。

## タブ補完（任意）

```bash
pip install speedtest-z[completion]
eval "$(register-python-argcomplete speedtest-z)"
```

`eval` の行を `~/.bashrc` や `~/.zshrc` に追記すると常時有効になります。
