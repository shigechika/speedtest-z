# CLAUDE.md

## 言語設定

- 会話・技術説明・コード内コメントはすべて日本語で記述する
- README.md は英語、README.ja.md は日本語

## プロジェクト概要

Selenium を使って複数の速度テストサイト（Cloudflare, Netflix/fast.com, Google Fiber, Ookla, Box-test, M-Lab, USEN, inonius）を自動実行し、結果を Zabbix へトラッパーアイテムとして送信するツール。

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

- `.github/workflows/ci.yml` — push/PR 時に構文チェック + ビルドテスト（Python 3.10, 3.12, 3.13）
- `.github/workflows/release.yml` — `v*` タグ push 時に PyPI へ自動公開（Trusted Publishers）

## 注意事項

- `config.ini` は `.gitignore` で除外（`config.ini-sample` をコピーして使用）
- Chrome ブラウザが実行環境に必要（pip では入らない）
- テストサイトの DOM 構造変更によりセレクタが壊れる可能性がある（定期的な確認が必要）
