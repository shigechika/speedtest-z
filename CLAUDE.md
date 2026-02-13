# CLAUDE.md

## 言語設定

- 会話・技術説明・コード内コメントはすべて日本語で記述する
- README.md は英語、README.ja.md は日本語

## プロジェクト概要

Selenium を使って複数の速度テストサイト（Cloudflare, Netflix/fast.com, Google Fiber, Ookla, Box-test, M-Lab, USEN, iNonius）を自動実行し、結果を Zabbix へトラッパーアイテムとして送信するツール。

## アーキテクチャ

- `speedtest_z/main.py` — メインスクリプト（SpeedtestZ クラス + CLI エントリポイント）
- `speedtest_z/__init__.py` — バージョン情報（setuptools-scm で自動採番）
- `config.ini` — 実行設定（探索順: CWD → ~/.config/speedtest-z/）
- `logging.ini` — ログ設定（同上）
- `deploy/` — systemd service/timer, cron（デプロイ参考用）
- `speedtest-z_templates.yaml` — Zabbix テンプレート

## コマンド

```bash
# 開発用インストール
python3 -m venv .venv
. .venv/bin/activate
pip install -e .

# 構文チェック
python3 -m py_compile speedtest_z/main.py

# CLI
speedtest-z --version
speedtest-z --list-sites
speedtest-z --dry-run
speedtest-z --dry-run cloudflare netflix

# パッケージビルド
pip install build
python -m build
```

## CI/CD

- `.github/workflows/ci.yml` — push/PR 時に構文チェック + ビルドテスト（Python 3.10〜3.14）
- `.github/workflows/release.yml` — `v*` タグ push 時に PyPI へ自動公開（Trusted Publishers）

## 注意事項

- `config.ini` は `.gitignore` で除外（`config.ini-sample` をコピーして使用）
- Chrome ブラウザが実行環境に必要（pip では入らない）
- テストサイトの DOM 構造変更によりセレクタが壊れる可能性がある（定期的な確認が必要）

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
