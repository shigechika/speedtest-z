# 使い方

```
speedtest-z [options] [site ...]
```

## CLIオプション

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

## 確認プロンプト

対話的なターミナル（TTY）から実行すると、テストサイトへの接続前に確認を求めます。cron や systemd、パイプ経由など非対話環境では自動的にスキップされます。

```
$ speedtest-z -n
speedtest-z: 8 サイトに接続します (cloudflare, netflix, ...)
続行しますか？ [y/N]: y
```

## 実行例

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

## 実行ログの例

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
