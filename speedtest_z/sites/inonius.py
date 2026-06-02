"""Site runner for iNonius Speed Test."""

from __future__ import annotations

import logging
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

URL = "https://inonius.net/speedtest/"

# Download display elements (IPv4 / IPv6) used to detect progress: they show a
# number once the test is actually running.
_PROGRESS_XPATHS = (
    "/html/body/div/astro-island/div/div[1]/div/div[1]/div[1]/div[1]/div/div/span[1]",  # IPv4_DL
    "/html/body/div/astro-island/div/div[2]/div/div[1]/div[1]/div[1]/div/div/span[1]",  # IPv6_DL
)


def _inonius_is_running(driver) -> bool:  # type: ignore[no-untyped-def]
    """Return True if a measurement value (a digit) is visible.

    Mere presence of the page container does not mean the test started, so
    this checks the download display elements for an actual numeric reading.
    """
    for xpath in _PROGRESS_XPATHS:
        try:
            if any(ch.isdigit() for ch in driver.find_element(By.XPATH, xpath).text):
                return True
        except (NoSuchElementException, StaleElementReferenceException):
            # Element absent or momentarily stale while polling: not yet running.
            continue
    return False


def _inonius_fallback_start(app: SpeedtestZ) -> bool:
    """Detect an auto-started iNonius test when the consent dialog was skipped.

    When cookies remember consent, the dialog may not appear and the test may
    start automatically.  Instead of trusting that the page merely loaded, this
    polls for an actual measurement value before declaring the test running, so
    a page that did *not* auto-start fails fast (with a snapshot) rather than
    falsely proceeding to a guaranteed completion-wait timeout.

    Returns True if a measurement is progressing, False otherwise.
    """
    try:
        WebDriverWait(app.driver, 15).until(_inonius_is_running)
        logger.info("inonius: Test is running (auto-started via cookie consent)")
        return True
    except TimeoutException:
        logger.error("inonius: Could not start test (no dialog, no measurement progress)")
        app.take_snapshot("inonius_error_fallback")
        return False


def run_inonius(app: SpeedtestZ) -> None:
    """Run iNonius speed test (inonius.net)."""
    if not app._should_run("inonius"):
        return

    try:
        logger.info("inonius: OPEN")
        if not app._load_with_retry(URL):
            return

        start_xpath = "/html/body/div/astro-island/dialog/div/div/form/button[2]"
        if app.auto_consent:
            # --yes: auto-click the consent dialog (accept and start in one)
            try:
                start_btn = WebDriverWait(app.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, start_xpath))
                )
                start_btn.click()
                logger.info("inonius: Consent accepted and started (auto)")
            except TimeoutException:
                # Dialog suppressed by cookie consent: fall back
                if not _inonius_fallback_start(app):
                    return
        else:
            # No --yes: wait for user action, or fall back if the dialog is suppressed by cookie
            try:
                dialog = WebDriverWait(app.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "dialog"))
                )
                # Once the dialog is shown, wait for the user to click and close it
                logger.info("inonius: Waiting for user to accept consent dialog...")
                WebDriverWait(app.driver, 120).until(lambda d: not dialog.is_displayed())
                logger.info("inonius: Dialog closed by user")
            except TimeoutException:
                # Dialog not shown (consent remembered by cookie): fall back
                if not _inonius_fallback_start(app):
                    return

        try:
            WebDriverWait(app.driver, 90).until(
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
            app.take_snapshot("inonius_timeout")
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
                val = app.driver.find_element(By.XPATH, xpath).text
                if key_suffix.endswith("_MSS"):
                    # Take the last token safely to avoid IndexError on empty text.
                    tokens = val.split()
                    val = tokens[-1] if tokens else ""
                if val:
                    full_key = f"inonius.{key_suffix}"
                    data.append(
                        {
                            "host": app.zabbix_host,
                            "key": full_key,
                            "value": val,
                        }
                    )
            except NoSuchElementException:
                logger.debug(f"inonius: Element not found for {key_suffix}")
            except Exception as e:
                logger.warning(f"inonius: Error processing {key_suffix}: {e}")

        logger.debug(f"inonius Result: {data}")
        app.send_results(data)

    except Exception as e:
        logger.error(f"inonius Error: {e}")
    finally:
        app.take_snapshot("inonius")
