"""Site runner for box-test.com Speed Test."""

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

URL = "https://www.box-test.com/"


def wait_for_stability(app: SpeedtestZ) -> None:
    """Wait for box-test results to stabilize (same value twice in a row).

    Polls the "Average latency to Box" chart element every 5 seconds
    (up to 12 iterations = 60 s) and returns once two consecutive
    readings match.
    """
    logger.info("Checking latency stability...")
    last_value = None
    xpath = (
        "//div[contains(text(), 'Average latency to Box')]"
        "/ancestor::div[contains(@class, 'card')]"
        "//*[local-name()='tspan' and contains(., 'Avg:')]"
    )
    for _ in range(12):
        try:
            element = app.driver.find_element(By.XPATH, xpath)
            current_value = element.text.strip()
            if current_value and current_value == last_value:
                logger.info(f"Stability reached: {current_value}")
                return
            last_value = current_value
        except NoSuchElementException:
            pass
        time.sleep(5)
    logger.warning("Timeout or not stabilized.")


def run_boxtest(app: SpeedtestZ) -> None:
    """Run box-test.com speed test."""
    if not app._should_run("boxtest"):
        return

    try:
        logger.info("boxtest: OPEN")
        if not app._load_with_retry(URL):
            return

        time.sleep(1)
        target_label = "100 MB"
        toggle_xpath = "//button[contains(., 'MB')]"

        for _i in range(5):
            try:
                toggle_btn = app.wait.until(EC.element_to_be_clickable((By.XPATH, toggle_xpath)))
                current_text = toggle_btn.text
                if target_label in current_text:
                    logger.info(f"boxtest: Target size reached: {current_text}")
                    break
                toggle_btn.click()
                time.sleep(1)
            except Exception as e:
                logger.warning(f"boxtest: Error switching size: {e}")
                break

        wait_for_stability(app)

        try:
            go_btn = app.driver.find_element(By.XPATH, "//button[contains(text(), 'Go!')]")
            go_btn.click()
            logger.info("boxtest: START")
        except Exception as e:
            logger.error(f"boxtest: Start button error: {e}")
            app.take_snapshot("boxtest_error_start")
            return

        upload_speed_xpath = "//div[@id='pop-test-manager']//table/tbody/tr/td[5]"

        def _box_finished(d):
            try:
                txt = d.find_element(By.XPATH, upload_speed_xpath).text.strip()
                return len(txt) > 0 and any(c.isdigit() for c in txt)
            except Exception:
                return False

        try:
            WebDriverWait(app.driver, app.BOXTEST_TIMEOUT).until(_box_finished)
            logger.info("boxtest: COMPLETED")
        except TimeoutException:
            logger.error("boxtest: Timeout waiting for results.")
            app.take_snapshot("boxtest_timeout")
            return

        base_xp = "//div[@id='pop-test-manager']//table/tbody/tr"
        latency_xp = (
            "//div[contains(text(), 'Average latency to Box')]"
            "/ancestor::div[contains(@class, 'card')]"
            "//*[local-name()='tspan' and contains(., 'Avg:')]"
        )

        # Numeric items
        numeric_items = {
            "DownloadSpeed": f"{base_xp}/td[2]",
            "DownloadDuration": f"{base_xp}/td[3]",
            "DownloadRTT": f"{base_xp}/td[4]",
            "UploadSpeed": f"{base_xp}/td[5]",
            "UploadDuration": f"{base_xp}/td[6]",
            "UploadRTT": f"{base_xp}/td[7]",
            "latency": latency_xp,
        }
        # String items (not split)
        string_items = {
            "POP": f"{base_xp}/td[1]/b",
        }

        data = []

        for key_suffix, xpath in string_items.items():
            try:
                val = app.driver.find_element(By.XPATH, xpath).text.strip()
                if val:
                    data.append(
                        {
                            "host": app.zabbix_host,
                            "key": f"boxtest.{key_suffix}",
                            "value": val,
                        }
                    )
            except NoSuchElementException:
                logger.warning(f"boxtest: Element not found: {key_suffix}")
            except Exception as e:
                logger.warning(f"boxtest: Error processing {key_suffix}: {e}")

        for key_suffix, xpath in numeric_items.items():
            try:
                val = app.driver.find_element(By.XPATH, xpath).text
                # Take the first token safely to avoid IndexError on empty text.
                tokens = val.replace("Avg:", "").replace("ms", "").strip().split()
                clean_val = tokens[0] if tokens else ""
                data.append(
                    {
                        "host": app.zabbix_host,
                        "key": f"boxtest.{key_suffix}",
                        "value": clean_val,
                    }
                )
            except NoSuchElementException:
                logger.warning(f"boxtest: Element not found: {key_suffix}")
            except Exception as e:
                logger.warning(f"boxtest: Error processing {key_suffix}: {e}")

        logger.debug(f"boxtest Result: {data}")
        app.send_results(data)

    except Exception as e:
        logger.error(f"boxtest Error: {e}")
    finally:
        # Single snapshot in finally (consistent with the other site runners),
        # so a snapshot is captured on early return too.
        app.take_snapshot("boxtest")
