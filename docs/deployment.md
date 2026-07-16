# Deployment (systemd)

> **Note:** The `.deb` and `.rpm` packages include systemd service/timer files pre-configured. Just run `sudo systemctl enable --now speedtest-z.timer` after installing.

For manual (pip) installations, the `deploy/` directory contains systemd unit files for scheduled execution:

| File | Description |
|------|-------------|
| `speedtest-z.service` | Service unit (runs `speedtest-z` as the `speedtest-z` user -- edit `ExecStart` / `User` to match your setup) |
| `speedtest-z.timer` | Timer unit (runs every 10 minutes) |
| `SeleniumCleaner.cron` | Cron job to clean up stale Chrome temp files |

## Setup

The service unit sets `User=` / `Group=`, so install it as a **system** unit (user units under `~/.config/systemd/user/` cannot switch users and will fail):

```bash
# Copy unit files
sudo cp deploy/speedtest-z.service /etc/systemd/system/
sudo cp deploy/speedtest-z.timer /etc/systemd/system/

# Edit the ExecStart path / User for your environment, then:
sudo systemctl daemon-reload
sudo systemctl enable --now speedtest-z.timer

# Check status
systemctl status speedtest-z.timer
systemctl list-timers speedtest-z.timer
```

Optionally, install the cron job for cleaning up stale Chrome temporary directories:

```bash
sudo cp deploy/SeleniumCleaner.cron /etc/cron.d/SeleniumCleaner
```
