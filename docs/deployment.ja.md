# デプロイ（systemd）

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

## Selenium クリーナー（cron）

Chrome の一時ファイルを定期的に削除する cron 設定も含まれています。

```bash
sudo cp deploy/SeleniumCleaner.cron /etc/cron.d/SeleniumCleaner
```
