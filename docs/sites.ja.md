# 対応テストサイト

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
