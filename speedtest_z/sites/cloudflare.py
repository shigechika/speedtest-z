"""Site runner for Cloudflare Speed Test."""

from __future__ import annotations

import logging
import re
import time
from typing import TYPE_CHECKING

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

    from speedtest_z.runner import SpeedtestZ

logger = logging.getLogger("speedtest-z")

URL = "https://speed.cloudflare.com/"


def _extract_by_label(
    driver: WebDriver, label_text: str, unit_pattern: str = r"Mbps|ms|\u03bcs|us"
) -> str:
    """Extract a numeric value from the Cloudflare results page by label.

    Searches for a ``<div>`` whose text matches *label_text*, walks up
    to the parent element, and extracts the first number followed by a
    matching unit string.

    Args:
        driver: Selenium WebDriver instance.
        label_text: The visible label text (e.g. ``"Download"``).
        unit_pattern: Regex alternation of expected unit strings.

    Returns:
        The extracted numeric string, or ``""`` if extraction fails.
        Microsecond values (``\u03bcs`` / ``us``) are converted to
        milliseconds.
    """
    try:
        label_el = driver.find_element(By.XPATH, f"//div[text()='{label_text}']")
        parent = label_el.find_element(By.XPATH, "./..")
        text_content = parent.text

        if not any(char.isdigit() for char in text_content):
            text_content = parent.find_element(By.XPATH, "./..").text

        if label_text in text_content:
            parts = text_content.split(label_text)
            target_text = parts[1] if len(parts) > 1 else text_content
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
            if "\u03bc" in unit_str or "u" in unit_str:
                value = value / 1000.0
                return f"{value:.3f}"
            return f"{value}"

    except (NoSuchElementException, Exception):
        pass
    return ""


def run_cloudflare(app: SpeedtestZ) -> None:
    """Run Cloudflare Speed Test (speed.cloudflare.com)."""
    if not app._should_run("cloudflare"):
        return

    try:
        logger.info("cloudflare: OPEN")
        if not app._load_with_retry(URL):
            return

        try:
            time.sleep(5)
            start_btn = WebDriverWait(app.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Start')]"))
            )
            start_btn.click()
            logger.info("cloudflare: 'Start' button clicked")

            WebDriverWait(app.driver, 10).until(EC.invisibility_of_element(start_btn))
            logger.info("cloudflare: Test started")

        except TimeoutException:
            logger.warning("cloudflare: Start button issue. Continuing...")
        except Exception as e:
            logger.warning(f"cloudflare: Error clicking Start button: {e}")

        logger.debug("cloudflare: Measuring... (Waiting for Quality Scores)")

        try:
            WebDriverWait(app.driver, 90).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[contains(text(), 'Video Streaming')]")
                )
            )
            logger.info("cloudflare: COMPLETED (Quality Scores appeared)")
            time.sleep(3)
        except TimeoutException:
            logger.warning("cloudflare: Timeout waiting for completion.")
            app.take_snapshot("cloudflare_timeout")

        try:
            download = _extract_by_label(app.driver, "Download", "Mbps")
            upload = _extract_by_label(app.driver, "Upload", "Mbps")
            latency = _extract_by_label(app.driver, "Latency", "ms")
            jitter = _extract_by_label(app.driver, "Jitter", r"ms|\u03bcs|us")

            logger.debug(f"cloudflare Result: {download=} {upload=} {latency=} {jitter=}")

            if not download:
                logger.error("cloudflare: Failed to extract download speed.")
                app.take_snapshot("cloudflare_error_parse")
                return

            data = [
                {
                    "host": app.zabbix_host,
                    "key": "cloudflare.download",
                    "value": download,
                },
                {
                    "host": app.zabbix_host,
                    "key": "cloudflare.upload",
                    "value": upload,
                },
                {
                    "host": app.zabbix_host,
                    "key": "cloudflare.latency",
                    "value": latency,
                },
                {
                    "host": app.zabbix_host,
                    "key": "cloudflare.jitter",
                    "value": jitter,
                },
            ]
            app.send_results(data)

        except Exception as e:
            logger.error(f"cloudflare: Error extracting results: {e}")
            return

    except Exception as e:
        logger.error(f"cloudflare Error: {e}")
    finally:
        app.take_snapshot("cloudflare")
