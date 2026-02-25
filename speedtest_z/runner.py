"""Core runner: SpeedtestZ class with WebDriver management and shared methods."""

from __future__ import annotations

import argparse
import configparser
import logging
import os
import platform
import random
import re
import signal
import sys
import time
import types as types_mod

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from zappix.sender import Sender, SenderData

from speedtest_z.config import _find_config
from speedtest_z.i18n import _msg

logger = logging.getLogger("speedtest-z")


class SpeedtestZ:
    """Browser-based speed test runner with Zabbix integration."""

    # Class constants
    DEFAULT_TIMEOUT = 45
    BOXTEST_TIMEOUT = 90
    WINDOW_WIDTH = 1024
    WINDOW_HEIGHT = 1024
    MAX_RETRIES = 3
    RETRY_DELAY = 5

    def __init__(self, args: argparse.Namespace | None = None) -> None:
        """Initialize SpeedtestZ with CLI arguments and config file."""
        # 設定ファイルの読み込み
        self.config = configparser.ConfigParser()
        config_path = _find_config("config.ini", getattr(args, "config", None))
        if config_path:
            self.config.read(config_path)
            logger.info(f"Config loaded: {config_path}")
        else:
            logger.warning(_msg("config_not_found_fallback"))

        # [general] — dry_run を優先、なければ旧名 dryrun にフォールバック
        self.dryrun = self.config.getboolean("general", "dry_run", fallback=None)
        if self.dryrun is None:
            self.dryrun = self.config.getboolean("general", "dryrun", fallback=True)
        self.headless = self.config.getboolean("general", "headless", fallback=True)
        self.timeout = self.config.getint("general", "timeout", fallback=30)
        self.ookla_server = self.config.get("general", "ookla_server", fallback=None)
        self.chrome_profile_dir = os.path.expanduser(
            self.config.get(
                "general", "chrome_profile_dir", fallback="~/.config/speedtest-z/chrome-profile"
            )
        )

        # CLI 引数でオーバーライド
        self.explicit_sites = False
        self.auto_consent = False
        if args:
            if args.dry_run:
                self.dryrun = True
            if args.headless is not None:
                self.headless = args.headless
            if args.timeout is not None:
                self.timeout = args.timeout
            if args.sites:
                self.explicit_sites = True
            if getattr(args, "yes", False):
                self.auto_consent = True

        # [zabbix]
        self.zabbix_enable = self.config.getboolean("zabbix", "enable", fallback=False)
        self.zabbix_server = self.config.get("zabbix", "server", fallback="127.0.0.1")
        self.zabbix_port = self.config.getint("zabbix", "port", fallback=10051)
        self.zabbix_host = self.config.get("zabbix", "host", fallback="speedtest-agent")

        # [grafana]
        self.grafana_sender = None
        if self.config.has_section("grafana"):
            grafana_enable = self.config.getboolean("grafana", "enable", fallback=False)
            if grafana_enable:
                try:
                    from speedtest_z.grafana import GrafanaSender

                    url = self.config.get("grafana", "remote_write_url")
                    username = self.config.get("grafana", "username")
                    token = self.config.get("grafana", "token")
                    self.grafana_sender = GrafanaSender(url, username, token)
                except ImportError:
                    logger.error("cramjam not installed. Run: pip install speedtest-z[grafana]")
                except configparser.NoSectionError:
                    logger.error("[grafana] section missing required keys")
                except configparser.NoOptionError as e:
                    logger.error(f"[grafana] config incomplete: {e}")

        # [otel]
        self.otel_sender = None
        if self.config.has_section("otel"):
            otel_enable = self.config.getboolean("otel", "enable", fallback=False)
            if otel_enable:
                try:
                    from speedtest_z.otel import OtelSender

                    endpoint = self.config.get("otel", "endpoint")
                    headers_str = self.config.get("otel", "headers", fallback="")
                    # "Key1=Val1,Key2=Val2" → dict
                    headers = {}
                    for pair in headers_str.split(","):
                        pair = pair.strip()
                        if "=" in pair:
                            k, v = pair.split("=", 1)
                            headers[k.strip()] = v.strip()
                    self.otel_sender = OtelSender(endpoint, headers, self.zabbix_host)
                except ImportError:
                    logger.error("opentelemetry not installed. Run: pip install speedtest-z[otel]")
                except configparser.NoOptionError as e:
                    logger.error(f"[otel] config incomplete: {e}")

        # [snapshot]
        self.snapshot_enable = self.config.getboolean("snapshot", "enable", fallback=False)
        self.snapshot_dir = self.config.get("snapshot", "save_dir", fallback="./snapshots")
        if self.snapshot_enable and not os.path.exists(self.snapshot_dir):
            os.makedirs(self.snapshot_dir)

        # WebDriver の初期化
        self._init_driver()

        # SIGTERM ハンドリング
        signal.signal(signal.SIGTERM, self._handle_sigterm)

    def _handle_sigterm(self, signum: int, frame: types_mod.FrameType | None) -> None:
        """Handle SIGTERM signal for graceful shutdown."""
        logger.info("SIGTERM received, shutting down...")
        self.close()
        sys.exit(0)

    def _init_driver(self) -> None:
        """Initialize Chrome WebDriver."""
        logger.info("Initializing Chrome WebDriver...")

        options = webdriver.ChromeOptions()

        if self.headless:
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")

        options.add_argument(f"--window-size={self.WINDOW_WIDTH},{self.WINDOW_HEIGHT}")
        options.add_argument("--log-level=3")

        os.makedirs(self.chrome_profile_dir, exist_ok=True)
        options.add_argument(f"--user-data-dir={self.chrome_profile_dir}")
        logger.info(f"Chrome profile: {self.chrome_profile_dir}")

        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(60)

            self.wait = WebDriverWait(self.driver, self.timeout)
            self.action_chains = ActionChains(self.driver)

            if not self.headless:
                self.driver.set_window_size(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
                pos = self._get_window_position()
                if pos:
                    self.driver.set_window_position(*pos)
                    logger.info(f"Window moved to Top-Right: {pos}")

        except Exception as e:
            logger.error(_msg("chrome_init_failed", error=e))
            sys.exit(1)

    def _should_run(self, site_name: str) -> bool:
        """Determine whether to run a site based on frequency config."""
        if self.explicit_sites:
            return True

        frequency = self.config.getint("frequency", site_name, fallback=100)

        if frequency <= 0:
            logger.info(f"Skipping {site_name}: Frequency is 0 (Disabled)")
            return False

        if frequency >= 100:
            return True

        val = random.randint(1, 100)
        if val <= frequency:
            return True
        else:
            logger.info(f"Skipping {site_name}: Throttled({val=}) by frequency ({frequency}%)")
            return False

    def close(self) -> None:
        """Close the browser and clean up."""
        if hasattr(self, "driver"):
            logger.info("Closing browser session...")
            self.driver.quit()
        if hasattr(self, "otel_sender") and self.otel_sender:
            self.otel_sender.shutdown()

    def take_snapshot(self, filename_base: str) -> None:
        """Save a screenshot of the current page."""
        if not self.snapshot_enable:
            return

        try:
            filename = f"{filename_base}.png"
            filepath = os.path.join(self.snapshot_dir, filename)
            self.driver.save_screenshot(filepath)
            logger.debug(f"Snapshot saved: {filename}")
        except Exception as e:
            logger.warning(f"Failed to take snapshot: {e}")

    def send_results(self, data_list: list[dict[str, str]]) -> None:
        """Send measurement results to enabled backends (Zabbix, Grafana)."""
        if not data_list:
            return

        packet = []
        for item in data_list:
            hostname = item.get("host", self.zabbix_host)
            metric = SenderData(hostname, item["key"], item["value"])
            packet.append(metric)

        if self.dryrun:
            target_host = data_list[0].get("host", "unknown")
            logger.debug(f"Buffered for {target_host}: {data_list}")
            logger.debug("Dryrun: True - Data not sent.")
            return

        # Zabbix 送信
        if self.zabbix_enable:
            try:
                sender = Sender(self.zabbix_server, self.zabbix_port)
                res = sender.send_bulk(packet)
                logger.info(f"Zabbix Response: {res}")
            except Exception:
                logger.exception("Failed to send to Zabbix")

        # Grafana 送信
        if self.grafana_sender:
            try:
                self.grafana_sender.send(data_list)
            except Exception:
                logger.exception("Failed to send to Grafana")

        # OTel 送信
        if self.otel_sender:
            try:
                self.otel_sender.send(data_list)
            except Exception:
                logger.exception("Failed to send to OTel")

    def _get_window_position(self) -> tuple[int, int]:
        """Calculate top-right window position based on OS."""
        if platform.system() == "Linux":
            return self._get_position_linux()
        else:
            return self._get_position_via_driver()

    def _get_position_linux(self) -> tuple[int, int]:
        """Get screen width via xrandr on Linux."""
        try:
            import subprocess

            result = subprocess.run(
                ["xrandr", "--current"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if " connected" in line:
                    match = re.search(r"(\d+)x(\d+)", line)
                    if match:
                        screen_width = int(match.group(1))
                        x_pos = max(0, screen_width - self.WINDOW_WIDTH)
                        return (x_pos, 0)
        except Exception as e:
            logger.warning(f"Linux position calc failed: {e}")
        return (0, 0)

    def _get_position_via_driver(self) -> tuple[int, int]:
        """Get screen width via JavaScript on macOS/Windows."""
        try:
            screen_width = self.driver.execute_script("return window.screen.availWidth")
            if screen_width:
                x_pos = max(0, screen_width - self.WINDOW_WIDTH)
                return (x_pos, 0)
        except Exception as e:
            logger.warning(f"JS position calc failed: {e}")
        return (0, 0)

    def _load_with_retry(
        self, url: str, max_retries: int | None = None, delay: int | None = None
    ) -> bool:
        """Load a URL with retry logic."""
        if max_retries is None:
            max_retries = self.MAX_RETRIES
        if delay is None:
            delay = self.RETRY_DELAY

        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                time.sleep(2)
                page = self.driver.page_source.lower()
                error_indicators = [
                    "can't be reached",
                    "err_",
                    "dns_probe",
                    "connection refused",
                    "took too long",
                ]

                if not any(err in page for err in error_indicators):
                    return True
                logger.warning(f"Page load failed (attempt {attempt + 1}/{max_retries}): {url}")
            except Exception as e:
                logger.warning(f"Page load exception (attempt {attempt + 1}/{max_retries}): {e}")

            if attempt < max_retries - 1:
                time.sleep(delay)

        logger.error(f"Failed to load after {max_retries} attempts: {url}")
        return False
