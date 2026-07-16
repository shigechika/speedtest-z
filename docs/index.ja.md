# speedtest-z

speedtest-z は Web ブラウザで主要な速度テストサイトを自動巡回。ユーザ体験そのままの回線品質を定点観測できます。

- 8つの速度テストサイトに対応（Cloudflare, Netflix, Ookla, M-Lab 等）
- Zabbix 連携で回線品質を継続監視
- `pip install speedtest-z` ですぐ使える

![デモ - 8サイト速度テスト結果](demo.gif)

導入は[インストール](install.md)、CLI の使い方は[使い方](usage.md)へ。

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

## 計測結果を共有しませんか？

爆速回線や激遅 Wi-Fi の計測結果をお待ちしています！

[GitHub Issues](https://github.com/shigechika/speedtest-z/issues/new?template=speedtest-result.yml) から以下を添えて投稿してください:
- `snapshots/` ディレクトリのスクリーンショット
- CLI ログ出力（`speedtest-z --dry-run`）

データセンターの超高速回線でも、山小屋の激遅 Wi-Fi でも大歓迎です。

## License

[Apache License 2.0](https://github.com/shigechika/speedtest-z/blob/main/LICENSE)

Copyright 2026 AIKAWA Shigechika
