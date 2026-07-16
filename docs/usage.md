# Usage

```
speedtest-z [options] [site ...]
```

## Options

| Option | Description |
|--------|-------------|
| `-V`, `--version` | Show program version and exit |
| `-c`, `--config CONFIG` | Config file path (default: `./config.ini` or `~/.config/speedtest-z/config.ini`) |
| `-n`, `--dry-run` | Test run (do not send data to Zabbix) |
| `--headless` | Run Chrome in headless mode |
| `--no-headless`, `--headed` | Run Chrome with GUI (non-headless) |
| `--timeout SECONDS` | Timeout in seconds for each test |
| `--list-sites` | List available test sites and exit |
| `--check` | Check site URL reachability and exit (no Chrome needed) |
| `-o`, `--output FORMAT` | Output format: `zabbix` (default), `json`, `csv` |
| `-d`, `--debug` | Enable debug output |
| `site` | Positional argument(s): test site(s) to run (default: all) |

## Confirmation Prompt

When run from an interactive terminal (TTY), speedtest-z asks for confirmation before connecting to test sites. Non-interactive environments (cron, systemd, piped input) skip the prompt automatically.

```
$ speedtest-z -n
speedtest-z: connecting to 8 site(s) (cloudflare, netflix, ...)
Continue? [y/N]: y
```

## Examples

```bash
# Run all test sites (dry-run)
speedtest-z -n

# Run specific sites
speedtest-z cloudflare netflix

# Run with GUI browser for debugging
speedtest-z --no-headless -d cloudflare

# List available sites
speedtest-z --list-sites

# Check if all test site URLs are reachable (no Chrome needed)
speedtest-z --check

# Check specific sites only
speedtest-z --check cloudflare netflix

# Output results as JSON (Zabbix send is skipped)
speedtest-z --dry-run --output json cloudflare 2>/dev/null

# Output results as CSV
speedtest-z --dry-run -o csv cloudflare netflix 2>/dev/null
```

## Example Output

```
$ speedtest-z --dry-run
speedtest-z: connecting to 8 site(s) (cloudflare, netflix, google, ookla, boxtest, mlab, usen, inonius)
Continue? [y/N]: y
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

All 8 sites completed in about 6 minutes.
