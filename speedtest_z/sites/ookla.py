"""Site runner for Ookla Speedtest."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

if TYPE_CHECKING:
    from speedtest_z.runner import SpeedtestZ

logger = logging.getLogger("speedtest-z")

URL = "https://www.speedtest.net/"


def run_ookla(app: SpeedtestZ) -> None:
    """Run Ookla Speedtest (speedtest.net)."""
    if not app._should_run("ookla"):
        return

    for attempt in range(app.MAX_RETRIES):
        try:
            logger.info(f"ookla: OPEN (Attempt {attempt + 1}/{app.MAX_RETRIES})")

            if attempt > 0:
                logger.info("ookla: Reloading page...")
                app.driver.refresh()
                time.sleep(5)
            else:
                if not app._load_with_retry(URL):
                    return

            if app.auto_consent:
                try:
                    consent = WebDriverWait(app.driver, 5).until(
                        EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
                    )
                    app.driver.execute_script("arguments[0].click();", consent)
                    logger.info("ookla: Consent accepted (auto)")
                except TimeoutException:
                    logger.debug("ookla: Consent dialog not found (auto)")
            else:
                # バナーが出ていたらユーザが「Continue」をクリックするまで待つ
                try:
                    banner = WebDriverWait(app.driver, 5).until(
                        EC.visibility_of_element_located((By.ID, "onetrust-banner-sdk"))
                    )
                    logger.info("ookla: Waiting for user to accept privacy banner...")
                    WebDriverWait(app.driver, 120).until(EC.invisibility_of_element(banner))
                    logger.info("ookla: Privacy banner dismissed by user")
                except TimeoutException:
                    logger.debug("ookla: Privacy banner not found or not dismissed")

            # Server Selection
            if app.ookla_server is not None:
                need_change = True
                try:
                    curr_srv_elem = WebDriverWait(app.driver, 10).until(
                        EC.visibility_of_element_located((By.CLASS_NAME, "hostUrl"))
                    )
                    if app.ookla_server in curr_srv_elem.text:
                        logger.info(f"ookla: Server match ({curr_srv_elem.text}).")
                        need_change = False
                except Exception as e:
                    logger.debug(f"ookla: Could not read current server: {e}")

                if need_change:
                    logger.info("ookla: Search [Change Server]")
                    is_success = False
                    for _ in range(3):
                        try:
                            xp = app.wait.until(
                                EC.element_to_be_clickable((By.LINK_TEXT, "Change Server"))
                            )
                            xp.click()
                            is_success = True
                            break
                        except Exception as e:
                            logger.debug(f"ookla: Change Server click retry: {e}")
                            time.sleep(1)

                    if not is_success:
                        try:
                            xp = app.driver.find_element(
                                By.XPATH,
                                "//a[contains(text(), 'Change Server')]",
                            )
                            app.driver.execute_script("arguments[0].click();", xp)
                            is_success = True
                        except Exception as e:
                            logger.debug(f"ookla: Change Server JS fallback failed: {e}")

                    if is_success:
                        try:
                            search_box = app.wait.until(
                                EC.visibility_of_element_located((By.ID, "host-search"))
                            )
                            search_box.clear()
                            search_box.send_keys(app.ookla_server)
                            app.wait.until(
                                EC.presence_of_element_located(
                                    (
                                        By.XPATH,
                                        '//*[@id="find-servers"]//ul/li/a',
                                    )
                                )
                            )
                            time.sleep(1)
                            server_list = app.driver.find_elements(
                                By.XPATH,
                                '//*[@id="find-servers"]//ul/li/a',
                            )
                            target_found = False
                            for item in server_list:
                                if app.ookla_server in item.text:
                                    item.click()
                                    target_found = True
                                    break
                            if not target_found and server_list:
                                server_list[0].click()
                        except Exception as e:
                            logger.warning(f"ookla: Server selection failed: {e}")

            try:
                start_btn = app.wait.until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "start-text"))
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
                        if d.find_element(By.CLASS_NAME, "result-data-large").is_displayed():
                            dl = d.find_element(By.CLASS_NAME, "download-speed").text
                            ul = d.find_element(By.CLASS_NAME, "upload-speed").text
                            if (
                                dl
                                and ul
                                and dl not in ["\u2014", "-"]
                                and ul not in ["\u2014", "-"]
                            ):
                                return "SUCCESS"
                    except NoSuchElementException:
                        pass
                except StaleElementReferenceException:
                    pass
                return False

            try:
                status = WebDriverWait(app.driver, 90).until(_check_result_or_error)
            except TimeoutException:
                logger.error("ookla: Timeout waiting for results.")
                status = "TIMEOUT"

            if status == "ERROR":
                logger.warning("ookla: Detected Error Popup. Retrying...")
                app.take_snapshot(f"ookla_error_{attempt + 1}")
                continue
            elif status == "TIMEOUT":
                app.take_snapshot(f"ookla_timeout_{attempt + 1}")
                continue

            logger.info("ookla: COMPLETED")
            time.sleep(2)

            download = app.driver.find_element(By.CLASS_NAME, "download-speed").text
            upload = app.driver.find_element(By.CLASS_NAME, "upload-speed").text
            ping = app.driver.find_element(By.CLASS_NAME, "ping-speed").text

            logger.debug(f"ookla Result: {download=} {upload=} {ping=}")

            data = [
                {
                    "host": app.zabbix_host,
                    "key": "ookla.download",
                    "value": download,
                },
                {
                    "host": app.zabbix_host,
                    "key": "ookla.upload",
                    "value": upload,
                },
                {
                    "host": app.zabbix_host,
                    "key": "ookla.ping",
                    "value": ping,
                },
            ]
            app.send_results(data)
            app.take_snapshot("ookla")
            return

        except Exception as e:
            logger.error(f"ookla Error (Attempt {attempt + 1}): {e}")
            app.take_snapshot(f"ookla_exception_{attempt + 1}")
            time.sleep(3)

    logger.error("ookla: Failed after all retries.")
