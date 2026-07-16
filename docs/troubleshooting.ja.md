# トラブルシューティング

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
