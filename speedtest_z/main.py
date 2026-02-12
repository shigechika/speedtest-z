#!/usr/bin/env python3
"""speedtest-z: 複数サイトの速度テストを自動実行し Zabbix に送信する"""

import sys
import time
import logging
import logging.config
import random
import os
import signal
import argparse
import configparser
import re
import platform

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)

# Zabbix Imports
from zappix.sender import Sender, SenderData

from speedtest_z import __version__

logger = logging.getLogger("speedtest-z")

# 利用可能なテストサイト一覧
AVAILABLE_SITES = [
    "cloudflare",
    "netflix",
    "google",
    "ookla",
    "boxtest",
    "mlab",
    "usen",
    "inonius",
]


def _find_config(name, cli_path=None):
    """設定ファイルを探索順に返す

    1. CLI で指定されたパス
    2. カレントディレクトリ
    3. ~/.config/speedtest-z/（XDG_CONFIG_HOME）
    """
    if cli_path:
        if os.path.isfile(cli_path):
            return cli_path
        logger.warning(f"{cli_path} が見つかりません")
        return None

    if os.path.isfile(name):
        return name

    xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    xdg_path = os.path.join(xdg, "speedtest-z", name)
    if os.path.isfile(xdg_path):
        return xdg_path

    return None


def _setup_logging(debug=False):
    """logging 設定を初期化"""
    logging_ini = _find_config("logging.ini")
    if logging_ini:
        logging.config.fileConfig(logging_ini, disable_existing_loggers=False)
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )


class SpeedtestZ:
    # クラス定数
    DEFAULT_TIMEOUT = 45
    BOXTEST_TIMEOUT = 90
    WINDOW_WIDTH = 1024
    WINDOW_HEIGHT = 1024
    MAX_RETRIES = 3
    RETRY_DELAY = 5

    def __init__(self, args=None):
        # 設定ファイルの読み込み
        self.config = configparser.ConfigParser()
        config_path = _find_config("config.ini", getattr(args, "config", None))
        if config_path:
            self.config.read(config_path)
            logger.info(f"Config loaded: {config_path}")
        else:
            logger.warning(
                "config.ini が見つかりません。デフォルト設定で動作します。\n"
                "  config.ini-sample を以下のいずれかにコピーしてください:\n"
                "    ./config.ini\n"
                "    ~/.config/speedtest-z/config.ini"
            )

        # [general]
        self.dryrun = self.config.getboolean("general", "dryrun", fallback=True)
        self.headless = self.config.getboolean("general", "headless", fallback=True)
        self.timeout = self.config.getint("general", "timeout", fallback=30)
        self.ookla_server = self.config.get("general", "ookla_server", fallback=None)

        # CLI 引数でオーバーライド
        self.explicit_sites = False
        if args:
            if args.dry_run:
                self.dryrun = True
            if args.headless is not None:
                self.headless = args.headless
            if args.timeout is not None:
                self.timeout = args.timeout
            if args.sites:
                self.explicit_sites = True

        # [zabbix]
        self.zabbix_server = self.config.get("zabbix", "server", fallback="127.0.0.1")
        self.zabbix_port = self.config.getint("zabbix", "port", fallback=10051)
        self.zabbix_host = self.config.get(
            "zabbix", "host", fallback="speedtest-agent"
        )

        # [snapshot]
        self.snapshot_enable = self.config.getboolean(
            "snapshot", "enable", fallback=False
        )
        self.snapshot_dir = self.config.get(
            "snapshot", "save_dir", fallback="./snapshots"
        )
        if self.snapshot_enable and not os.path.exists(self.snapshot_dir):
            os.makedirs(self.snapshot_dir)

        # WebDriver の初期化
        self._init_driver()

        # SIGTERM ハンドリング
        signal.signal(signal.SIGTERM, self._handle_sigterm)

    def _handle_sigterm(self, signum, frame):
        """SIGTERM を受けて graceful shutdown"""
        logger.info("SIGTERM received, shutting down...")
        self.close()
        sys.exit(0)

    def _init_driver(self):
        """Chrome Driver の初期化"""
        logger.info("Initializing Chrome WebDriver...")

        options = webdriver.ChromeOptions()

        if self.headless:
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")

        options.add_argument(
            f"--window-size={self.WINDOW_WIDTH},{self.WINDOW_HEIGHT}"
        )
        options.add_argument("--log-level=3")

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
            logger.error(
                f"Chrome WebDriver の初期化に失敗しました: {e}\n"
                "  Google Chrome がインストールされているか確認してください。\n"
                "  https://www.google.com/chrome/"
            )
            sys.exit(1)

    def _should_run(self, site_name):
        """実行判定: CLI でサイト明示指定時は常に実行、それ以外は [frequency] を参照"""
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
            logger.info(
                f"Skipping {site_name}: Throttled({val=}) by frequency ({frequency}%)"
            )
            return False

    def close(self):
        """ブラウザ終了処理"""
        if hasattr(self, "driver"):
            logger.info("Closing browser session...")
            self.driver.quit()

    def take_snapshot(self, filename_base):
        """スクリーンショット保存"""
        if not self.snapshot_enable:
            return

        try:
            filename = f"{filename_base}.png"
            filepath = os.path.join(self.snapshot_dir, filename)
            self.driver.save_screenshot(filepath)
            logger.debug(f"Snapshot saved: {filename}")
        except Exception as e:
            logger.warning(f"Failed to take snapshot: {e}")

    def send_to_zabbix(self, data_list):
        """Zabbix へデータ送信"""
        if not data_list:
            return

        packet = []
        for item in data_list:
            hostname = item.get("host", self.zabbix_host)
            metric = SenderData(hostname, item["key"], item["value"])
            packet.append(metric)

        if self.dryrun:
            target_host = data_list[0].get("host", "unknown")
            logger.info(f"Buffered for {target_host}: {data_list}")
            logger.info("Dryrun: True - Data not sent.")
            return

        try:
            sender = Sender(self.zabbix_server, self.zabbix_port)
            res = sender.send(packet)
            logger.info(f"Zabbix Response: {res}")
        except Exception as e:
            logger.error(f"Failed to send to Zabbix: {e}")

    def _get_window_position(self) -> tuple:
        """OS に応じてウィンドウ位置(右上)を計算"""
        if platform.system() == "Linux":
            return self._get_position_linux()
        else:
            return self._get_position_via_driver()

    def _get_position_linux(self) -> tuple:
        """Linux 環境用: xrandr で画面幅を取得"""
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

    def _get_position_via_driver(self) -> tuple:
        """macOS/Windows 用: JavaScript で画面幅を取得"""
        try:
            screen_width = self.driver.execute_script(
                "return window.screen.availWidth"
            )
            if screen_width:
                x_pos = max(0, screen_width - self.WINDOW_WIDTH)
                return (x_pos, 0)
        except Exception as e:
            logger.warning(f"JS position calc failed: {e}")
        return (0, 0)

    def _load_with_retry(
        self, url: str, max_retries: int = None, delay: int = None
    ) -> bool:
        """URL をリトライ付きでロードする"""
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
                logger.warning(
                    f"Page load failed (attempt {attempt + 1}/{max_retries}): {url}"
                )
            except Exception as e:
                logger.warning(
                    f"Page load exception (attempt {attempt + 1}/{max_retries}): {e}"
                )

            if attempt < max_retries - 1:
                time.sleep(delay)

        logger.error(f"Failed to load after {max_retries} attempts: {url}")
        return False

    # --- Test Modules ---

    def run_cloudflare(self):
        """Cloudflare Speed Test"""
        if not self._should_run("cloudflare"):
            return

        try:
            logger.info("cloudflare: OPEN")
            if not self._load_with_retry("https://speed.cloudflare.com/"):
                return

            try:
                time.sleep(5)
                start_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(., 'Start')]")
                    )
                )
                start_btn.click()
                logger.info("cloudflare: 'Start' button clicked")

                WebDriverWait(self.driver, 10).until(
                    EC.invisibility_of_element(start_btn)
                )
                logger.info("cloudflare: Test started")

            except TimeoutException:
                logger.warning("cloudflare: Start button issue. Continuing...")
            except Exception as e:
                logger.warning(f"cloudflare: Error clicking Start button: {e}")

            logger.debug("cloudflare: Measuring... (Waiting for Quality Scores)")

            try:
                WebDriverWait(self.driver, 90).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[contains(text(), 'Video Streaming')]")
                    )
                )
                logger.info("cloudflare: COMPLETED (Quality Scores appeared)")
                time.sleep(3)
            except TimeoutException:
                logger.warning("cloudflare: Timeout waiting for completion.")
                self.take_snapshot("cloudflare_timeout")

            try:

                def extract_by_label(label_text, unit_pattern=r"Mbps|ms|μs|us"):
                    try:
                        label_el = self.driver.find_element(
                            By.XPATH, f"//div[text()='{label_text}']"
                        )
                        parent = label_el.find_element(By.XPATH, "./..")
                        text_content = parent.text

                        if not any(char.isdigit() for char in text_content):
                            text_content = parent.find_element(
                                By.XPATH, "./.."
                            ).text

                        if label_text in text_content:
                            parts = text_content.split(label_text)
                            target_text = (
                                parts[1] if len(parts) > 1 else text_content
                            )
                        else:
                            target_text = text_content

                        match = re.search(
                            rf"([\d\.]+)\s*({unit_pattern})",
                            target_text,
                            re.IGNORECASE,
                        )

                        if match:
                            value_str = match.group(1)
                            unit_str = match.group(2).lower()
                            value = float(value_str)
                            if "μ" in unit_str or "u" in unit_str:
                                value = value / 1000.0
                                return f"{value:.3f}"
                            return f"{value}"

                    except (NoSuchElementException, Exception):
                        pass
                    return ""

                download = extract_by_label("Download", "Mbps")
                upload = extract_by_label("Upload", "Mbps")
                latency = extract_by_label("Latency", "ms")
                jitter = extract_by_label("Jitter", r"ms|μs|us")

                logger.debug(
                    f"cloudflare Result: {download=} {upload=} {latency=} {jitter=}"
                )

                if not download:
                    logger.error("cloudflare: Failed to extract download speed.")
                    self.take_snapshot("cloudflare_error_parse")
                    return

                data = [
                    {
                        "host": self.zabbix_host,
                        "key": "cloudflare.download",
                        "value": download,
                    },
                    {
                        "host": self.zabbix_host,
                        "key": "cloudflare.upload",
                        "value": upload,
                    },
                    {
                        "host": self.zabbix_host,
                        "key": "cloudflare.latency",
                        "value": latency,
                    },
                    {
                        "host": self.zabbix_host,
                        "key": "cloudflare.jitter",
                        "value": jitter,
                    },
                ]
                self.send_to_zabbix(data)

            except Exception as e:
                logger.error(f"cloudflare: Error extracting results: {e}")
                return

        except Exception as e:
            logger.error(f"cloudflare Error: {e}")
        finally:
            self.take_snapshot("cloudflare")

    def run_netflix(self):
        """fast.com (Netflix)"""
        if not self._should_run("netflix"):
            return

        try:
            logger.info("netflix: OPEN")
            if not self._load_with_retry("https://fast.com/"):
                return

            try:
                more_btn = self.wait.until(
                    EC.element_to_be_clickable((By.ID, "show-more-details-link"))
                )
                self.driver.execute_script("arguments[0].click();", more_btn)
                logger.info("netflix: MORE INFO CLICKED")
            except Exception as e:
                logger.error(f"netflix: Failed to click more details: {e}")
                self.take_snapshot("netflix_error_click")
                return

            try:
                WebDriverWait(self.driver, 90).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "#speed-progress-indicator.succeeded")
                    )
                )
                time.sleep(1)
                logger.info("netflix: COMPLETED (succeeded class detected)")
            except TimeoutException:
                logger.error("netflix: Timeout waiting for results.")
                self.take_snapshot("netflix_timeout")
                return

            try:
                download = self.driver.find_element(By.ID, "speed-value").text
                upload = self.driver.find_element(By.ID, "upload-value").text
                latency = self.driver.find_element(By.ID, "latency-value").text
                server_locations = self.driver.find_element(
                    By.ID, "server-locations"
                ).text

                logger.debug(
                    f"netflix: Result: {download=} {upload=} {latency=}"
                    f" {server_locations=}"
                )

                data = [
                    {
                        "host": self.zabbix_host,
                        "key": "netflix.download",
                        "value": download,
                    },
                    {
                        "host": self.zabbix_host,
                        "key": "netflix.upload",
                        "value": upload,
                    },
                    {
                        "host": self.zabbix_host,
                        "key": "netflix.latency",
                        "value": latency,
                    },
                    {
                        "host": self.zabbix_host,
                        "key": "netflix.server-locations",
                        "value": server_locations,
                    },
                ]
                self.send_to_zabbix(data)

            except NoSuchElementException as e:
                logger.error(f"netflix: Result elements not found. {e}")
                return

        except Exception as e:
            logger.error(f"netflix Error: {e}")
        finally:
            self.take_snapshot("netflix")

    def run_google(self):
        """Google Fiber Speedtest"""
        if not self._should_run("google"):
            return

        try:
            logger.info("google: OPEN")
            if not self._load_with_retry("https://speed.googlefiber.net/"):
                return

            time.sleep(3)
            try:
                start_btn = self.wait.until(
                    EC.element_to_be_clickable((By.ID, "run-test"))
                )
                start_btn.click()
                logger.info("google: Initial Start Clicked")
            except Exception as e:
                logger.error(f"google: Start button not found. {e}")
                self.take_snapshot("google_error_start")
                return

            try:
                continue_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, ".actionButton-confirmSpeedtest")
                    )
                )
                continue_btn.click()
                logger.info("google: Popup 'CONTINUE' Clicked")
            except TimeoutException:
                pass
            except Exception as e:
                logger.warning(f"google: Popup handling warning: {e}")

            logger.info("google: Measuring...")

            def _google_finished(d):
                try:
                    download = d.find_element(
                        By.CSS_SELECTOR, "span[name='downloadSpeedMbps']"
                    ).text
                    upload = d.find_element(
                        By.CSS_SELECTOR, "span[name='uploadSpeedMbps']"
                    ).text
                    return download and upload and any(c.isdigit() for c in download) and any(c.isdigit() for c in upload)
                except Exception:
                    return False

            try:
                WebDriverWait(self.driver, 60).until(_google_finished)
                time.sleep(3)
                logger.info("google: COMPLETED")
            except TimeoutException:
                logger.error("google: Timeout waiting for results.")
                self.take_snapshot("google_timeout")
                return

            try:
                download = self.driver.find_element(
                    By.CSS_SELECTOR, "span[name='downloadSpeedMbps']"
                ).text
                upload = self.driver.find_element(
                    By.CSS_SELECTOR, "span[name='uploadSpeedMbps']"
                ).text
                ping = self.driver.find_element(
                    By.CSS_SELECTOR, "span[name='ping']"
                ).text

                logger.debug(f"google: Result: {download=} {upload=} {ping=}")

                data = [
                    {
                        "host": self.zabbix_host,
                        "key": "google.download",
                        "value": download,
                    },
                    {
                        "host": self.zabbix_host,
                        "key": "google.upload",
                        "value": upload,
                    },
                    {
                        "host": self.zabbix_host,
                        "key": "google.ping",
                        "value": ping,
                    },
                ]
                self.send_to_zabbix(data)

            except Exception as e:
                logger.error(f"google: Error reading results: {e}")
                return

        except Exception as e:
            logger.error(f"google Error: {e}")
        finally:
            self.take_snapshot("google")

    def run_ookla(self):
        """Ookla Speedtest (speedtest.net)"""
        if not self._should_run("ookla"):
            return

        for attempt in range(self.MAX_RETRIES):
            try:
                logger.info(
                    f"ookla: OPEN (Attempt {attempt + 1}/{self.MAX_RETRIES})"
                )

                if attempt > 0:
                    logger.info("ookla: Reloading page...")
                    self.driver.refresh()
                    time.sleep(5)
                else:
                    if not self._load_with_retry("https://www.speedtest.net/"):
                        return

                try:
                    consent = self.wait.until(
                        EC.element_to_be_clickable(
                            (By.ID, "onetrust-accept-btn-handler")
                        )
                    )
                    self.driver.execute_script("arguments[0].click();", consent)
                except TimeoutException:
                    pass

                # Server Selection
                if self.ookla_server is not None:
                    need_change = True
                    try:
                        curr_srv_elem = WebDriverWait(self.driver, 10).until(
                            EC.visibility_of_element_located(
                                (By.CLASS_NAME, "hostUrl")
                            )
                        )
                        if self.ookla_server in curr_srv_elem.text:
                            logger.info(
                                f"ookla: Server match ({curr_srv_elem.text})."
                            )
                            need_change = False
                    except Exception:
                        pass

                    if need_change:
                        logger.info("ookla: Search [Change Server]")
                        is_success = False
                        for _ in range(3):
                            try:
                                xp = self.wait.until(
                                    EC.element_to_be_clickable(
                                        (By.LINK_TEXT, "Change Server")
                                    )
                                )
                                xp.click()
                                is_success = True
                                break
                            except Exception:
                                time.sleep(1)

                        if not is_success:
                            try:
                                xp = self.driver.find_element(
                                    By.XPATH,
                                    "//a[contains(text(), 'Change Server')]",
                                )
                                self.driver.execute_script(
                                    "arguments[0].click();", xp
                                )
                                is_success = True
                            except Exception:
                                pass

                        if is_success:
                            try:
                                search_box = self.wait.until(
                                    EC.visibility_of_element_located(
                                        (By.ID, "host-search")
                                    )
                                )
                                search_box.clear()
                                search_box.send_keys(self.ookla_server)
                                self.wait.until(
                                    EC.presence_of_element_located(
                                        (
                                            By.XPATH,
                                            '//*[@id="find-servers"]//ul/li/a',
                                        )
                                    )
                                )
                                time.sleep(1)
                                server_list = self.driver.find_elements(
                                    By.XPATH,
                                    '//*[@id="find-servers"]//ul/li/a',
                                )
                                target_found = False
                                for item in server_list:
                                    if self.ookla_server in item.text:
                                        item.click()
                                        target_found = True
                                        break
                                if not target_found and server_list:
                                    server_list[0].click()
                            except Exception as e:
                                logger.warning(
                                    f"ookla: Server selection failed: {e}"
                                )

                try:
                    start_btn = self.wait.until(
                        EC.element_to_be_clickable(
                            (By.CLASS_NAME, "start-text")
                        )
                    )
                    start_btn.click()
                    logger.info("ookla: START")
                except Exception as e:
                    logger.warning(f"ookla: Start button error: {e}")
                    continue

                def _check_result_or_error(d):
                    try:
                        try:
                            if d.find_element(
                                By.CSS_SELECTOR,
                                ".error-container, .notification-error",
                            ).is_displayed():
                                return "ERROR"
                        except NoSuchElementException:
                            pass

                        try:
                            if d.find_element(
                                By.CLASS_NAME, "result-data-large"
                            ).is_displayed():
                                dl = d.find_element(
                                    By.CLASS_NAME, "download-speed"
                                ).text
                                ul = d.find_element(
                                    By.CLASS_NAME, "upload-speed"
                                ).text
                                if (
                                    dl
                                    and ul
                                    and dl not in ["—", "-"]
                                    and ul not in ["—", "-"]
                                ):
                                    return "SUCCESS"
                        except NoSuchElementException:
                            pass
                    except StaleElementReferenceException:
                        pass
                    return False

                try:
                    status = WebDriverWait(self.driver, 90).until(
                        _check_result_or_error
                    )
                except TimeoutException:
                    logger.error("ookla: Timeout waiting for results.")
                    status = "TIMEOUT"

                if status == "ERROR":
                    logger.warning("ookla: Detected Error Popup. Retrying...")
                    self.take_snapshot(f"ookla_error_{attempt + 1}")
                    continue
                elif status == "TIMEOUT":
                    self.take_snapshot(f"ookla_timeout_{attempt + 1}")
                    continue

                logger.info("ookla: COMPLETED")
                time.sleep(2)

                download = self.driver.find_element(
                    By.CLASS_NAME, "download-speed"
                ).text
                upload = self.driver.find_element(
                    By.CLASS_NAME, "upload-speed"
                ).text
                ping = self.driver.find_element(
                    By.CLASS_NAME, "ping-speed"
                ).text

                logger.debug(f"ookla Result: {download=} {upload=} {ping=}")

                data = [
                    {
                        "host": self.zabbix_host,
                        "key": "ookla.download",
                        "value": download,
                    },
                    {
                        "host": self.zabbix_host,
                        "key": "ookla.upload",
                        "value": upload,
                    },
                    {
                        "host": self.zabbix_host,
                        "key": "ookla.ping",
                        "value": ping,
                    },
                ]
                self.send_to_zabbix(data)
                self.take_snapshot("ookla")
                return

            except Exception as e:
                logger.error(f"ookla Error (Attempt {attempt + 1}): {e}")
                self.take_snapshot(f"ookla_exception_{attempt + 1}")
                time.sleep(3)

        logger.error("ookla: Failed after all retries.")

    def wait_for_stability(self):
        """box-test 用: 3 秒ごとにチェックし、前回と同じ値なら安定とみなす"""
        logger.info("Checking latency stability...")
        last_value = None
        xpath = (
            "//div[contains(text(), 'Average latency to Box')]"
            "/ancestor::div[contains(@class, 'card')]"
            "//*[local-name()='tspan' and contains(., 'Avg:')]"
        )
        for _ in range(12):
            try:
                element = self.driver.find_element(By.XPATH, xpath)
                current_value = element.text.strip()
                if current_value and current_value == last_value:
                    logger.info(f"Stability reached: {current_value}")
                    return
                last_value = current_value
            except NoSuchElementException:
                pass
            time.sleep(5)
        logger.warning("Timeout or not stabilized.")

    def run_boxtest(self):
        """box-test.com"""
        if not self._should_run("boxtest"):
            return

        try:
            logger.info("boxtest: OPEN")
            if not self._load_with_retry("https://www.box-test.com/"):
                return

            time.sleep(1)
            target_label = "100 MB"
            toggle_xpath = "//button[contains(., 'MB')]"

            for i in range(5):
                try:
                    toggle_btn = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, toggle_xpath))
                    )
                    current_text = toggle_btn.text
                    if target_label in current_text:
                        logger.info(
                            f"boxtest: Target size reached: {current_text}"
                        )
                        break
                    toggle_btn.click()
                    time.sleep(1)
                except Exception as e:
                    logger.warning(f"boxtest: Error switching size: {e}")
                    break

            self.wait_for_stability()

            try:
                go_btn = self.driver.find_element(
                    By.XPATH, "//button[contains(text(), 'Go!')]"
                )
                go_btn.click()
                logger.info("boxtest: START")
            except Exception as e:
                logger.error(f"boxtest: Start button error: {e}")
                self.take_snapshot("boxtest_error_start")
                return

            upload_speed_xpath = (
                "//div[@id='pop-test-manager']//table/tbody/tr/td[5]"
            )

            def _box_finished(d):
                try:
                    txt = d.find_element(By.XPATH, upload_speed_xpath).text.strip()
                    return len(txt) > 0 and any(c.isdigit() for c in txt)
                except Exception:
                    return False

            try:
                WebDriverWait(self.driver, self.BOXTEST_TIMEOUT).until(
                    _box_finished
                )
                logger.info("boxtest: COMPLETED")
            except TimeoutException:
                logger.error("boxtest: Timeout waiting for results.")
                self.take_snapshot("boxtest_timeout")
                return

            base_xp = "//div[@id='pop-test-manager']//table/tbody/tr"
            latency_xp = (
                "//div[contains(text(), 'Average latency to Box')]"
                "/ancestor::div[contains(@class, 'card')]"
                "//*[local-name()='tspan' and contains(., 'Avg:')]"
            )

            # 数値項目
            numeric_items = {
                "DownloadSpeed": f"{base_xp}/td[2]",
                "DownloadDuration": f"{base_xp}/td[3]",
                "DownloadRTT": f"{base_xp}/td[4]",
                "UploadSpeed": f"{base_xp}/td[5]",
                "UploadDuration": f"{base_xp}/td[6]",
                "UploadRTT": f"{base_xp}/td[7]",
                "latency": latency_xp,
            }
            # 文字列項目（split しない）
            string_items = {
                "POP": f"{base_xp}/td[1]/b",
            }

            data = []

            for key_suffix, xpath in string_items.items():
                try:
                    val = self.driver.find_element(By.XPATH, xpath).text.strip()
                    if val:
                        data.append(
                            {
                                "host": self.zabbix_host,
                                "key": f"boxtest.{key_suffix}",
                                "value": val,
                            }
                        )
                except NoSuchElementException:
                    logger.warning(f"boxtest: Element not found: {key_suffix}")
                except Exception as e:
                    logger.warning(
                        f"boxtest: Error processing {key_suffix}: {e}"
                    )

            for key_suffix, xpath in numeric_items.items():
                try:
                    val = self.driver.find_element(By.XPATH, xpath).text
                    clean_val = (
                        val.replace("Avg:", "")
                        .replace("ms", "")
                        .strip()
                        .split()[0]
                    )
                    data.append(
                        {
                            "host": self.zabbix_host,
                            "key": f"boxtest.{key_suffix}",
                            "value": clean_val,
                        }
                    )
                except NoSuchElementException:
                    logger.warning(f"boxtest: Element not found: {key_suffix}")
                except Exception as e:
                    logger.warning(
                        f"boxtest: Error processing {key_suffix}: {e}"
                    )

            logger.debug(f"boxtest Result: {data}")
            self.send_to_zabbix(data)
            self.take_snapshot("boxtest")

        except Exception as e:
            logger.error(f"boxtest Error: {e}")
        finally:
            self.take_snapshot("boxtest_final")

    def run_mlab(self):
        """M-Lab Speed Test (NDT)"""
        if not self._should_run("mlab"):
            return

        try:
            logger.info("mlab: OPEN")
            if not self._load_with_retry("https://speed.measurementlab.net/"):
                return

            try:
                chk_box = self.wait.until(
                    EC.presence_of_element_located((By.ID, "demo-human"))
                )
                self.driver.execute_script("arguments[0].click();", chk_box)
                logger.info("mlab: Consent Checked")
            except TimeoutException:
                pass

            try:
                start_btn = self.wait.until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "a.startButton")
                    )
                )
                start_btn.click()
                logger.info("mlab: START")
            except Exception as e:
                logger.error(f"mlab: Start button issue: {e}")
                self.take_snapshot("mlab_error_start")
                return

            logger.info("mlab: Waiting for finish (approx 45s)...")
            try:
                WebDriverWait(self.driver, 90).until(
                    EC.visibility_of_element_located(
                        (By.XPATH, "//span[contains(text(), 'Again')]")
                    )
                )
                logger.info("mlab: COMPLETED")
            except TimeoutException:
                logger.error("mlab: Timeout waiting for results.")
                self.take_snapshot("mlab_timeout")
                return

            base_xp = '//*[@id="measurementSpace"]//table/tbody'

            try:
                raw_dl = self.driver.find_element(
                    By.XPATH, f"{base_xp}/tr[3]/td[3]/strong"
                ).text
                download = raw_dl.split()[0]
                raw_ul = self.driver.find_element(
                    By.XPATH, f"{base_xp}/tr[4]/td[3]/strong"
                ).text
                upload = raw_ul.split()[0]
                raw_lat = self.driver.find_element(
                    By.XPATH, f"{base_xp}/tr[5]/td[3]/strong"
                ).text
                latency = raw_lat.split()[0]
                raw_retr = self.driver.find_element(
                    By.XPATH, f"{base_xp}/tr[6]/td[3]/strong"
                ).text
                retrans = raw_retr.replace("%", "").strip()

                logger.debug(
                    f"mlab Result: {download=} {upload=} {latency=} {retrans=}"
                )

                data = [
                    {
                        "host": self.zabbix_host,
                        "key": "mlab.download",
                        "value": download,
                    },
                    {
                        "host": self.zabbix_host,
                        "key": "mlab.upload",
                        "value": upload,
                    },
                    {
                        "host": self.zabbix_host,
                        "key": "mlab.latency",
                        "value": latency,
                    },
                    {
                        "host": self.zabbix_host,
                        "key": "mlab.retrans",
                        "value": retrans,
                    },
                ]
                self.send_to_zabbix(data)

            except Exception as e:
                logger.error(f"mlab: Error extracting results: {e}")
                return

        except Exception as e:
            logger.error(f"mlab Error: {e}")
        finally:
            self.take_snapshot("mlab")

    def run_usen(self):
        """USEN GATE 02"""
        if not self._should_run("usen"):
            return

        try:
            logger.info("usen: OPEN")
            if not self._load_with_retry("https://speedtest.gate02.ne.jp/"):
                return

            btn_selector = ".speedtest_start .btn-start"

            try:
                start_btn = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, btn_selector))
                )
                start_btn.click()
                logger.info("usen: START")
            except Exception as e:
                logger.error(f"usen: Start button not found. {e}")
                self.take_snapshot("usen_error_start")
                return

            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: "speedtest_wait"
                    in d.find_element(By.TAG_NAME, "body").get_attribute("class")
                )
                logger.info(
                    "usen: Measuring... (speedtest_wait class detected)"
                )
            except TimeoutException:
                logger.warning(
                    "usen: 'speedtest_wait' class did not appear. Starting anyway?"
                )

            logger.info("usen: Waiting for results (approx 60s)...")
            try:
                WebDriverWait(self.driver, 120).until(
                    lambda d: "speedtest_wait"
                    not in d.find_element(By.TAG_NAME, "body").get_attribute(
                        "class"
                    )
                )
                time.sleep(2)
                logger.info("usen: COMPLETED (speedtest_wait class removed)")
            except TimeoutException:
                logger.error("usen: Timeout waiting for completion.")
                self.take_snapshot("usen_timeout")
                return

            try:
                download = self.driver.find_element(By.ID, "dlText").text
                upload = self.driver.find_element(By.ID, "ulText").text
                ping = self.driver.find_element(By.ID, "pingText").text
                jitter = self.driver.find_element(By.ID, "jitText").text

                logger.debug(
                    f"usen Result: {download=} {upload=} {ping=} {jitter=}"
                )

                data = [
                    {
                        "host": self.zabbix_host,
                        "key": "usen.download",
                        "value": download,
                    },
                    {
                        "host": self.zabbix_host,
                        "key": "usen.upload",
                        "value": upload,
                    },
                    {
                        "host": self.zabbix_host,
                        "key": "usen.ping",
                        "value": ping,
                    },
                    {
                        "host": self.zabbix_host,
                        "key": "usen.jitter",
                        "value": jitter,
                    },
                ]
                self.send_to_zabbix(data)

            except NoSuchElementException as e:
                logger.error(f"usen: Result elements not found. {e}")
                return

        except Exception as e:
            logger.error(f"usen Error: {e}")
        finally:
            self.take_snapshot("usen")

    def run_inonius(self):
        """inonius.net"""
        if not self._should_run("inonius"):
            return

        try:
            logger.info("inonius: OPEN")
            if not self._load_with_retry("https://inonius.net/speedtest/"):
                return

            start_xpath = (
                "/html/body/div/astro-island/dialog/div/div/form/button[2]"
            )
            try:
                start_btn = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, start_xpath))
                )
                start_btn.click()
                logger.info("inonius: START")
            except TimeoutException:
                logger.error("inonius: Start button not found.")
                self.take_snapshot("inonius_error_start")
                return

            try:
                WebDriverWait(self.driver, 90).until(
                    EC.text_to_be_present_in_element(
                        (
                            By.XPATH,
                            "/html/body/div/astro-island/div/div[3]/div/span",
                        ),
                        "Test completed!",
                    )
                )
                logger.info("inonius: COMPLETED")
            except TimeoutException:
                logger.error("inonius: Timeout waiting for completion.")
                self.take_snapshot("inonius_timeout")
                return

            xpath_map = {
                "IPv6_RTT": "/html/body/div/astro-island/div/div[2]/div/div[1]/div[2]/div[1]/div/span[1]",
                "IPv6_JIT": "/html/body/div/astro-island/div/div[2]/div/div[1]/div[2]/div[2]/div/span[1]",
                "IPv6_DL": "/html/body/div/astro-island/div/div[2]/div/div[1]/div[1]/div[1]/div/div/span[1]",
                "IPv6_UL": "/html/body/div/astro-island/div/div[2]/div/div[1]/div[1]/div[2]/div/div/span[1]",
                "IPv6_MSS": "/html/body/div/astro-island/div/div[2]/div/div[2]/p",
                "IPv4_RTT": "/html/body/div/astro-island/div/div[1]/div/div[1]/div[2]/div[1]/div/span[1]",
                "IPv4_JIT": "/html/body/div/astro-island/div/div[1]/div/div[1]/div[2]/div[2]/div/span[1]",
                "IPv4_DL": "/html/body/div/astro-island/div/div[1]/div/div[1]/div[1]/div[1]/div/div/span[1]",
                "IPv4_UL": "/html/body/div/astro-island/div/div[1]/div/div[1]/div[1]/div[2]/div/div/span[1]",
                "IPv4_MSS": "/html/body/div/astro-island/div/div[1]/div/div[2]/p[1]",
            }

            data = []
            for key_suffix, xpath in xpath_map.items():
                try:
                    val = self.driver.find_element(By.XPATH, xpath).text
                    if key_suffix.endswith("_MSS"):
                        val = val.split()[-1]
                    if val:
                        full_key = f"inonius.{key_suffix}"
                        data.append(
                            {
                                "host": self.zabbix_host,
                                "key": full_key,
                                "value": val,
                            }
                        )
                except NoSuchElementException:
                    logger.debug(
                        f"inonius: Element not found for {key_suffix}"
                    )
                except Exception as e:
                    logger.warning(
                        f"inonius: Error processing {key_suffix}: {e}"
                    )

            logger.debug(f"inonius Result: {data}")
            self.send_to_zabbix(data)

        except Exception as e:
            logger.error(f"inonius Error: {e}")
        finally:
            self.take_snapshot("inonius")


def _build_parser():
    """argparse パーサーを構築"""
    parser = argparse.ArgumentParser(
        prog="speedtest-z",
        description="Automated multi-site speed test runner with Zabbix integration",
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-c",
        "--config",
        metavar="CONFIG",
        help="config file path (default: ./config.ini or ~/.config/speedtest-z/config.ini)",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="test run (do not send data to Zabbix)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=None,
        dest="headless",
        help="run Chrome in headless mode",
    )
    parser.add_argument(
        "--no-headless",
        "--headed",
        action="store_false",
        dest="headless",
        help="run Chrome with GUI (non-headless)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        metavar="SECONDS",
        help="timeout in seconds for each test",
    )
    parser.add_argument(
        "--list-sites",
        action="store_true",
        help="list available test sites and exit",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="enable debug output",
    )
    parser.add_argument(
        "sites",
        nargs="*",
        metavar="site",
        choices=AVAILABLE_SITES + [[]],
        help=f"test sites to run (default: all). choices: {', '.join(AVAILABLE_SITES)}",
    )
    return parser


def main():
    """エントリポイント"""
    parser = _build_parser()
    args = parser.parse_args()

    # --list-sites は Chrome 不要で応答
    if args.list_sites:
        print("Available test sites:")
        for site in AVAILABLE_SITES:
            print(f"  {site}")
        return

    # logging 設定（--debug 対応）
    _setup_logging(debug=args.debug)

    logger.info("speedtest-z: START")

    app = SpeedtestZ(args)
    try:
        sites = args.sites if args.sites else AVAILABLE_SITES
        site_runners = {
            "cloudflare": app.run_cloudflare,
            "netflix": app.run_netflix,
            "google": app.run_google,
            "ookla": app.run_ookla,
            "boxtest": app.run_boxtest,
            "mlab": app.run_mlab,
            "usen": app.run_usen,
            "inonius": app.run_inonius,
        }
        for site in sites:
            runner = site_runners.get(site)
            if runner:
                runner()
            else:
                logger.warning(f"Unknown site: {site}")
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal Error: {e}")
    finally:
        app.close()

    logger.info("speedtest-z: FINISH")


if __name__ == "__main__":
    main()
