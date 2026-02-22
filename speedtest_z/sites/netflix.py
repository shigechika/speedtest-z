"""Site runner for Netflix fast.com Speed Test."""

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

URL = "https://fast.com/"


def run_netflix(app: SpeedtestZ) -> None:
    """Run Netflix fast.com speed test."""
    if not app._should_run("netflix"):
        return

    try:
        logger.info("netflix: OPEN")
        if not app._load_with_retry(URL):
            return

        try:
            more_btn = app.wait.until(
                EC.element_to_be_clickable((By.ID, "show-more-details-link"))
            )
            app.driver.execute_script("arguments[0].click();", more_btn)
            logger.info("netflix: MORE INFO CLICKED")
        except Exception as e:
            logger.error(f"netflix: Failed to click more details: {e}")
            app.take_snapshot("netflix_error_click")
            return

        try:
            WebDriverWait(app.driver, 90).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#speed-progress-indicator.succeeded")
                )
            )
            time.sleep(1)
            logger.info("netflix: COMPLETED (succeeded class detected)")
        except TimeoutException:
            logger.error("netflix: Timeout waiting for results.")
            app.take_snapshot("netflix_timeout")
            return

        try:
            download = app.driver.find_element(By.ID, "speed-value").text
            upload = app.driver.find_element(By.ID, "upload-value").text
            latency = app.driver.find_element(By.ID, "latency-value").text
            server_locations = app.driver.find_element(By.ID, "server-locations").text

            logger.debug(f"netflix: Result: {download=} {upload=} {latency=} {server_locations=}")

            data = [
                {
                    "host": app.zabbix_host,
                    "key": "netflix.download",
                    "value": download,
                },
                {
                    "host": app.zabbix_host,
                    "key": "netflix.upload",
                    "value": upload,
                },
                {
                    "host": app.zabbix_host,
                    "key": "netflix.latency",
                    "value": latency,
                },
                {
                    "host": app.zabbix_host,
                    "key": "netflix.server-locations",
                    "value": server_locations,
                },
            ]
            app.send_results(data)

        except NoSuchElementException as e:
            logger.error(f"netflix: Result elements not found. {e}")
            return

    except Exception as e:
        logger.error(f"netflix Error: {e}")
    finally:
        app.take_snapshot("netflix")
