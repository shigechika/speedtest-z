# Deployment (systemd)

> **Note:** The `.deb` and `.rpm` packages include systemd service/timer files pre-configured. Just run `sudo systemctl enable --now speedtest-z.timer` after installing.

For manual (pip) installations, the `deploy/` directory contains systemd unit files for scheduled execution:

| File | Description |
|------|-------------|
| `speedtest-z.service` | Service unit (runs `speedtest-z` from the venv) |
| `speedtest-z.timer` | Timer unit (runs every 6 minutes) |
| `SeleniumCleaner.cron` | Cron job to clean up stale Chrome temp files |

## Setup

```bash
# Copy unit files
cp deploy/speedtest-z.service ~/.config/systemd/user/
cp deploy/speedtest-z.timer ~/.config/systemd/user/

# Reload and enable
systemctl --user daemon-reload
systemctl --user enable --now speedtest-z.timer

# Check status
systemctl --user status speedtest-z.timer
systemctl --user list-timers
```

Optionally, install the cron job for cleaning up stale Chrome temporary directories:

```bash
sudo cp deploy/SeleniumCleaner.cron /etc/cron.d/SeleniumCleaner
```
