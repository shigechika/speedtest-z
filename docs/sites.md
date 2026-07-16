# Supported Test Sites

| Site | URL | Metrics (Zabbix keys) |
|------|-----|----------------------|
| `cloudflare` | https://speed.cloudflare.com/ | download, upload, latency, jitter |
| `netflix` | https://fast.com/ | download, upload, latency, server-locations |
| `google` | http://speed.googlefiber.net/ | download, upload, ping |
| `ookla` | https://www.speedtest.net/ | download, upload, ping |
| `boxtest` | https://www.box-test.com/ | POP, DownloadSpeed, DownloadDuration, DownloadRTT, UploadSpeed, UploadDuration, UploadRTT, latency |
| `mlab` | https://speed.measurementlab.net/ | download, upload, latency, retrans |
| `usen` | https://speedtest.gate02.ne.jp/ | download, upload, ping, jitter |
| `inonius` | https://inonius.net/speedtest/ | IPv4/IPv6: DL, UL, RTT, JIT, MSS |

All Zabbix item keys are prefixed with the site name (e.g., `cloudflare.download`, `usen.ping`, `inonius.IPv4_DL`).

> **Note: Google Fiber (speed.googlefiber.net) and jumbo frames**
>
> speed.googlefiber.net does not support HTTPS (HTTP only) and has no AAAA records. In IPv6-only environments it is accessed via DNS64/NAT64, but **if the NIC MTU is set to 9000 (jumbo frames), the page JavaScript fails to load and the screen stays blank**. Set the MTU to 1500.
