"""Site runner for M-Lab Speed Test."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

if TYPE_CHECKING:
    from speedtest_z.runner import SpeedtestZ

logger = logging.getLogger("speedtest-z")

URL = "https://speed.measurementlab.net/"


def run_mlab(app: SpeedtestZ) -> None:
    """Run M-Lab Speed Test (speed.measurementlab.net)."""
    if not app._should_run("mlab"):
        return

    try:
        logger.info("mlab: OPEN")
        if not app._load_with_retry(URL):
            return

        if app.auto_consent:
            try:
                chk_box = app.wait.until(EC.presence_of_element_located((By.ID, "demo-human")))
                app.driver.execute_script("arguments[0].click();", chk_box)
                logger.info("mlab: Consent checked (auto)")
            except TimeoutException:
                pass
        else:
            # ユーザがチェックボックスをクリックするまで待つ
            try:
                chk_box = WebDriverWait(app.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "demo-human"))
                )
                if not chk_box.is_selected():
                    logger.info("mlab: Waiting for user to check consent checkbox...")
                    WebDriverWait(app.driver, 120).until(
                        lambda d: d.find_element(By.ID, "demo-human").is_selected()
                    )
                    logger.info("mlab: Consent checked by user")
            except TimeoutException:
                pass

        try:
            start_btn = app.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.startButton"))
            )
            start_btn.click()
            logger.info("mlab: START")
        except Exception as e:
            logger.error(f"mlab: Start button issue: {e}")
            app.take_snapshot("mlab_error_start")
            return

        logger.info("mlab: Waiting for finish (approx 45s)...")
        try:
            WebDriverWait(app.driver, 90).until(
                EC.visibility_of_element_located((By.XPATH, "//span[contains(text(), 'Again')]"))
            )
            logger.info("mlab: COMPLETED")
        except TimeoutException:
            logger.error("mlab: Timeout waiting for results.")
            app.take_snapshot("mlab_timeout")
            return

        base_xp = '//*[@id="measurementSpace"]//table/tbody'

        try:
            raw_dl = app.driver.find_element(By.XPATH, f"{base_xp}/tr[3]/td[3]/strong").text
            download = raw_dl.split()[0]
            raw_ul = app.driver.find_element(By.XPATH, f"{base_xp}/tr[4]/td[3]/strong").text
            upload = raw_ul.split()[0]
            raw_lat = app.driver.find_element(By.XPATH, f"{base_xp}/tr[5]/td[3]/strong").text
            latency = raw_lat.split()[0]
            raw_retr = app.driver.find_element(By.XPATH, f"{base_xp}/tr[6]/td[3]/strong").text
            retrans = raw_retr.replace("%", "").strip()

            logger.debug(f"mlab Result: {download=} {upload=} {latency=} {retrans=}")

            data = [
                {
                    "host": app.zabbix_host,
                    "key": "mlab.download",
                    "value": download,
                },
                {
                    "host": app.zabbix_host,
                    "key": "mlab.upload",
                    "value": upload,
                },
                {
                    "host": app.zabbix_host,
                    "key": "mlab.latency",
                    "value": latency,
                },
                {
                    "host": app.zabbix_host,
                    "key": "mlab.retrans",
                    "value": retrans,
                },
            ]
            app.send_to_zabbix(data)

        except Exception as e:
            logger.error(f"mlab: Error extracting results: {e}")
            return

    except Exception as e:
        logger.error(f"mlab Error: {e}")
    finally:
        app.take_snapshot("mlab")
