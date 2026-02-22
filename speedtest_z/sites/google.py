"""Site runner for Google Fiber Speed Test."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

if TYPE_CHECKING:
    from speedtest_z.runner import SpeedtestZ

logger = logging.getLogger("speedtest-z")

# 注意: speed.googlefiber.net は HTTPS 非対応（HTTP のみ）
URL = "http://speed.googlefiber.net/"


def run_google(app: SpeedtestZ) -> None:
    """Run Google Fiber Speedtest (speed.googlefiber.net)."""
    if not app._should_run("google"):
        return

    try:
        logger.info("google: OPEN")
        # 注意: speed.googlefiber.net は HTTPS 非対応（HTTP のみ）
        if not app._load_with_retry(URL):
            return

        time.sleep(3)
        try:
            start_btn = app.wait.until(EC.element_to_be_clickable((By.ID, "run-test")))
            start_btn.click()
            logger.info("google: Initial Start Clicked")
        except Exception as e:
            logger.error(f"google: Start button not found. {e}")
            app.take_snapshot("google_error_start")
            return

        try:
            continue_btn = WebDriverWait(app.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".actionButton-confirmSpeedtest"))
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
                download = d.find_element(By.CSS_SELECTOR, "span[name='downloadSpeedMbps']").text
                upload = d.find_element(By.CSS_SELECTOR, "span[name='uploadSpeedMbps']").text
                return (
                    download
                    and upload
                    and any(c.isdigit() for c in download)
                    and any(c.isdigit() for c in upload)
                )
            except Exception:
                return False

        try:
            WebDriverWait(app.driver, 60).until(_google_finished)
            time.sleep(3)
            logger.info("google: COMPLETED")
        except TimeoutException:
            logger.error("google: Timeout waiting for results.")
            app.take_snapshot("google_timeout")
            return

        try:
            download = app.driver.find_element(
                By.CSS_SELECTOR, "span[name='downloadSpeedMbps']"
            ).text
            upload = app.driver.find_element(By.CSS_SELECTOR, "span[name='uploadSpeedMbps']").text
            ping = app.driver.find_element(By.CSS_SELECTOR, "span[name='ping']").text

            logger.debug(f"google: Result: {download=} {upload=} {ping=}")

            data = [
                {
                    "host": app.zabbix_host,
                    "key": "google.download",
                    "value": download,
                },
                {
                    "host": app.zabbix_host,
                    "key": "google.upload",
                    "value": upload,
                },
                {
                    "host": app.zabbix_host,
                    "key": "google.ping",
                    "value": ping,
                },
            ]
            app.send_to_zabbix(data)

        except Exception as e:
            logger.error(f"google: Error reading results: {e}")
            return

    except Exception as e:
        logger.error(f"google Error: {e}")
    finally:
        app.take_snapshot("google")
