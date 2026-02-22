"""Site runner for USEN GATE 02 Speed Test."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

if TYPE_CHECKING:
    from speedtest_z.runner import SpeedtestZ

logger = logging.getLogger("speedtest-z")

URL = "https://speedtest.gate02.ne.jp/"


def run_usen(app: SpeedtestZ) -> None:
    """Run USEN GATE 02 speed test (speedtest.gate02.ne.jp)."""
    if not app._should_run("usen"):
        return

    try:
        logger.info("usen: OPEN")
        if not app._load_with_retry(URL):
            return

        btn_selector = ".speedtest_start .btn-start"

        try:
            start_btn = app.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, btn_selector)))
            start_btn.click()
            logger.info("usen: START")
        except Exception as e:
            logger.error(f"usen: Start button not found. {e}")
            app.take_snapshot("usen_error_start")
            return

        try:
            WebDriverWait(app.driver, 10).until(
                lambda d: (
                    "speedtest_wait" in d.find_element(By.TAG_NAME, "body").get_attribute("class")
                )
            )
            logger.info("usen: Measuring... (speedtest_wait class detected)")
        except TimeoutException:
            logger.warning("usen: 'speedtest_wait' class did not appear. Starting anyway?")

        logger.info("usen: Waiting for results (approx 60s)...")
        try:
            WebDriverWait(app.driver, 120).until(
                lambda d: (
                    "speedtest_wait"
                    not in d.find_element(By.TAG_NAME, "body").get_attribute("class")
                )
            )
            time.sleep(2)
            logger.info("usen: COMPLETED (speedtest_wait class removed)")
        except TimeoutException:
            logger.error("usen: Timeout waiting for completion.")
            app.take_snapshot("usen_timeout")
            return

        try:
            download = app.driver.find_element(By.ID, "dlText").text
            upload = app.driver.find_element(By.ID, "ulText").text
            ping = app.driver.find_element(By.ID, "pingText").text
            jitter = app.driver.find_element(By.ID, "jitText").text

            logger.debug(f"usen Result: {download=} {upload=} {ping=} {jitter=}")

            data = [
                {
                    "host": app.zabbix_host,
                    "key": "usen.download",
                    "value": download,
                },
                {
                    "host": app.zabbix_host,
                    "key": "usen.upload",
                    "value": upload,
                },
                {
                    "host": app.zabbix_host,
                    "key": "usen.ping",
                    "value": ping,
                },
                {
                    "host": app.zabbix_host,
                    "key": "usen.jitter",
                    "value": jitter,
                },
            ]
            app.send_results(data)

        except NoSuchElementException as e:
            logger.error(f"usen: Result elements not found. {e}")
            return

    except Exception as e:
        logger.error(f"usen Error: {e}")
    finally:
        app.take_snapshot("usen")
