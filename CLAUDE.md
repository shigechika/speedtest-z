# CLAUDE.md

## 言語設定

- 会話・技術説明は日本語で記述する
- コード内コメント・docstring は英語で記述する（public リポジトリのため。既存の日本語コメントは順次英語へ移行）
- README.md は英語、README.ja.md は日本語

## プロジェクト概要

Selenium を使って複数の速度テストサイト（Cloudflare, Netflix/fast.com, Google Fiber, Ookla, Box-test, M-Lab, USEN, iNonius）を自動実行し、結果を Zabbix や Grafana Cloud へ送信するツール。

## アーキテクチャ

- `speedtest_z/cli.py` — CLI エントリポイント（`main()`）
- `speedtest_z/runner.py` — SpeedtestZ コアクラス（WebDriver 管理・サイト実行オーケストレーション）
- `speedtest_z/sender.py` — SenderManager（Zabbix/Grafana/OTel バックエンド一括管理）。`set_version_tag()` で Zabbix host tag `speedtest-z=<version>` を付与（要 `pip install speedtest-z[zabbix-api]` ＝ zapi-lib）
- `speedtest_z/grafana.py` — Grafana Cloud Prometheus Remote Write 送信（Protobuf エンコーダー + GrafanaSender）
- `speedtest_z/otel.py` — OpenTelemetry OTLP 送信（OtelSender、要 `pip install speedtest-z[otel]`）
- `speedtest_z/config.py` — 設定ファイル探索・ログ設定
- `speedtest_z/i18n.py` — ロケール判定・メッセージ辞書
- `speedtest_z/output.py` — JSON/CSV 出力（OutputCollector、MetricSender 互換）
- `speedtest_z/healthcheck.py` — `--check` URL 疎通確認
- `speedtest_z/types.py` — ZabbixItem TypedDict + MetricSender プロトコル
- `speedtest_z/sites/` — サイトごとのランナー（`run_xxx(app)` 関数）
- `speedtest_z/__init__.py` — バージョン情報（`importlib.metadata` で取得。バージョンは `pyproject.toml` の静的 `version` を release-please が管理）
- `config.ini` — 実行設定（探索順: CLI → CWD → ~/.config/speedtest-z/ → /etc/speedtest-z/）
- `logging.ini` — ログ設定（同上、コンソールは stderr 出力）
- `deploy/` — systemd service/timer, cron（手動デプロイ参考用）
- `debian/` — .deb パッケージング設定（dh-virtualenv）
- `rpm/` — .rpm パッケージング用スクリプト（fpm でビルド）
- `speedtest-z_templates.yaml` — Zabbix テンプレート

## コマンド

```bash
# 開発用インストール
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
# Grafana Cloud 連携を使う場合
pip install -e ".[grafana]"
# OpenTelemetry (OTLP) 連携を使う場合
pip install -e ".[otel]"

# lint / format
ruff check speedtest_z/ tests/
ruff format --check speedtest_z/ tests/

# テスト（OTel テストは opentelemetry 未インストール時に自動スキップ）
pytest tests/ -v

# CLI
speedtest-z --version
speedtest-z --list-sites
speedtest-z --check
speedtest-z --dry-run
speedtest-z --dry-run cloudflare netflix
speedtest-z --dry-run --output json cloudflare

# パッケージビルド
pip install build
python -m build
```

## CI/CD

- `.github/workflows/ci.yml` — push/PR 時に構文チェック + ビルドテスト（Python 3.10〜3.14）
- `.github/workflows/release-please.yml` — main への push 時に release-please が Release PR を維持。マージで `vX.Y.Z` タグと GitHub Release を自動作成
- `.github/workflows/release.yml` — Release 公開時（`release: published`）に PyPI へ自動公開（Trusted Publishers）。`verify` ジョブで pyproject の version とタグの一致を確認
- `.github/workflows/deb.yml` — Release 公開時に jammy/noble 向け .deb ビルド → 当該 Release にアップロード（手動は workflow_dispatch）
- `.github/workflows/rpm.yml` — Release 公開時に Rocky 9 向け .rpm ビルド（fpm）→ 当該 Release にアップロード（手動は workflow_dispatch）

## リリース手順（release-please）

バージョン管理は **release-please** が担当する。`pyproject.toml` の静的 `version` と `CHANGELOG.md` は release-please が自動更新する（手動編集しない）。

1. **Conventional Commits** で main にマージする（`feat:` → minor、`fix:` → patch、`feat!:`/`BREAKING CHANGE` → 1.0 未満は minor）
2. release-please が **Release PR** を自動で開く/更新する（次バージョン + CHANGELOG エントリを含む）
3. README 等の更新が必要なら通常の PR で先に入れておく
4. Release PR をマージすると `vX.Y.Z` タグと GitHub Release が公開され、その `release: published` イベントで `release.yml`（PyPI）・`deb.yml`・`rpm.yml` が発火する

**重要: Release 起動には PAT が必要。** release-please が `GITHUB_TOKEN` で公開した Release は他ワークフローを起動しない（GitHub の仕様）。リポジトリシークレット `RELEASE_PLEASE_TOKEN`（PAT もしくは GitHub App トークン）を設定すると、release-please が公開する Release の `release: published` で PyPI/deb/rpm が自動発火する。未設定時は release-please 自体は動くが、ビルド/公開は手動発火（`deb.yml`/`rpm.yml` の workflow_dispatch 等）が必要。

**重要: PyPI はバージョンの上書きを許可しない。** release-please は常に新しいバージョンを採番するためこの問題は基本的に起きないが、公開済みバージョンの再公開はできない点に留意する。

## config.ini の設計

- `[general]` の `dry_run`（旧名 `dryrun` もフォールバックでサポート）。`chrome_profile_dir`（Cookie/同意の永続化先、デフォルト `~/.config/speedtest-z/chrome-profile`）
- `[zabbix]` に `enable` フラグ（デフォルト `false`）。`enable = true` で Zabbix 送信が有効
- `[zabbix]` の `api_url` / `api_user` / `api_password`（任意・3つ揃えると有効）。全サイト完走後に host tag `speedtest-z=<version>` を Zabbix JSON-RPC API で付与（`SenderManager.set_version_tag()` → `runner.stamp_version()`）。`--dry-run` / Zabbix 無効 / 未設定 / `--output json,csv` では no-op
- `[grafana]` セクション（オプション）。`enable = true` + `remote_write_url` / `username` / `token` で Grafana Cloud 送信
- `[otel]` セクション（オプション）。`enable = true` + `endpoint` / `headers` で OTLP 送信
- `--dry-run` 時は Zabbix も Grafana も OTel も送信しない（外部送信を全て止める一貫したルール）
- `--output json/csv` 時は stdout 出力のみ（バックエンド送信なし）。ログは stderr に出力されるため `2>/dev/null` で抑制可能
- `cramjam` は optional dependency: `pip install speedtest-z[grafana]`
- `opentelemetry-*` は optional dependency: `pip install speedtest-z[otel]`
- `zapi-lib` は optional dependency: `pip install speedtest-z[zabbix-api]`（host tag 用。httpx のみ依存で MCP スタックは引かない。.deb/.rpm は extras に含めてビルド）
- `SenderManager.send()` が全バックエンド（Zabbix + Grafana + OTel）への送信を一括管理
- `--output json/csv` 時は `OutputCollector` が `SenderManager` の代わりに `app.sender` に差し替わる（`MetricSender` プロトコル準拠）

## コーディングルール

- **Python ファイルを編集したら、コミット前に必ず `ruff format` と `ruff check` を実行すること**
  - `ruff format speedtest_z/ tests/` — 自動整形
  - `ruff check speedtest_z/ tests/` — lint チェック
  - CI で `ruff format --check` が走るため、未整形のままコミットすると CI が失敗する
  - 過去に2回この失敗でパッチバージョンを消費している（v0.8.2 等）

## 注意事項

- `config.ini` は `.gitignore` で除外（`config.ini-sample` をコピーして使用）
- Chrome ブラウザが実行環境に必要（pip では入らない）
- テストサイトの DOM 構造変更によりセレクタが壊れる可能性がある（定期的な確認が必要）
- `-y` / `--yes` は隠しオプション（`argparse.SUPPRESS`）。README や CHANGELOG に記載しないこと
- Linux 環境で日本語サイト（USEN, iNonius）のスナップショットがお豆腐になる場合は `apt install fonts-noto-cjk`

## README スクリーンショットの差し替え手順

README に埋め込む animation GIF (`docs/demo.gif`) の更新手順。

```bash
# 1. 全サイト計測（snapshot が snapshots/ に保存される）
speedtest-z --dry-run

# 2. frequency でスキップされたサイトがあれば明示指定で再実行
speedtest-z --dry-run ookla mlab

# 3. 8サイト分の PNG から animation GIF を生成（3秒/枚、640px幅）
magick \
  -delay 300x100 snapshots/cloudflare.png \
  -delay 300x100 snapshots/netflix.png \
  -delay 300x100 snapshots/google.png \
  -delay 300x100 snapshots/ookla.png \
  -delay 300x100 snapshots/boxtest.png \
  -delay 300x100 snapshots/mlab.png \
  -delay 300x100 snapshots/usen.png \
  -delay 300x100 snapshots/inonius.png \
  -resize 640x -loop 0 docs/demo.gif

# 4. ブラウザで確認（macOS Preview は GIF アニメ非対応）
open -a "Google Chrome" docs/demo.gif

# 5. README への埋め込み（両方に追加）
#   README.md:    ![Demo](docs/demo.gif)
#   README.ja.md: ![デモ](docs/demo.gif)
```

- `magick` (ImageMagick) が必要: `brew install imagemagick`
- delay 値: 100=1秒, 200=2秒, 300=3秒（現在は3秒/枚を採用）
- ディゾルブ（`-morph`）はファイルサイズが大幅に増えるため不採用

## テストサイト固有の注意

- **Google Fiber** (`speed.googlefiber.net`): HTTPS 非対応。HTTP のみで接続すること。安易に https:// に変更しないこと
- **Netflix** (`fast.com`): `/ja/` 等の言語パスを付けない。ブラウザのロケールで自動判定される
