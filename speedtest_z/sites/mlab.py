"""Site runner for M-Lab Speed Test."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver
    from selenium.webdriver.remote.webelement import WebElement

    from speedtest_z.runner import SpeedtestZ

logger = logging.getLogger("speedtest-z")

URL = "https://speed.measurementlab.net/"

# Data-policy consent checkbox: current site id plus the legacy id
CONSENT_SELECTOR = "#privacyConsent, #demo-human"


# Both wait predicates return Literal[False] (not None) for the miss case:
# selenium's WebDriverWait.until() stubs narrow `Literal[False] | T` to `T`,
# so False keeps mypy happy at the call sites while None would not.


def _find_consent(driver: WebDriver) -> WebElement | Literal[False]:
    """Return the consent checkbox element, or False if not present."""
    try:
        return driver.find_element(By.CSS_SELECTOR, CONSENT_SELECTOR)
    except NoSuchElementException:
        return False


def _consent_checked(driver: WebDriver) -> bool:
    """Return True when the consent checkbox exists and is checked."""
    chk_box = _find_consent(driver)
    return bool(chk_box and chk_box.is_selected())


def _enabled_start_button(driver: WebDriver) -> WebElement | Literal[False]:
    """Return the start button once it no longer carries the disabled class."""
    try:
        btn = driver.find_element(By.CSS_SELECTOR, "a.startButton")
    except NoSuchElementException:
        return False
    if "disabled" in (btn.get_attribute("class") or ""):
        return False
    return btn


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
                chk_box = app.wait.until(_find_consent)
                if chk_box.is_selected():
                    logger.info("mlab: Consent already checked")
                else:
                    app.driver.execute_script("arguments[0].click();", chk_box)
                    logger.info("mlab: Consent checked (auto)")
            except TimeoutException:
                logger.debug("mlab: Consent checkbox not found (auto)")
        else:
            # Wait for the user to click the checkbox
            try:
                chk_box = WebDriverWait(app.driver, 5).until(_find_consent)
                if not chk_box.is_selected():
                    logger.info("mlab: Waiting for user to check consent checkbox...")
                    WebDriverWait(app.driver, 120).until(_consent_checked)
                    logger.info("mlab: Consent checked by user")
            except TimeoutException:
                logger.debug("mlab: Consent checkbox not found or not checked")

        try:
            # The button keeps a "disabled" class until consent is given, and
            # an overlay can intercept a native click, so wait for the class to
            # clear and click via JavaScript.
            start_btn = app.wait.until(_enabled_start_button)
            app.driver.execute_script("arguments[0].click();", start_btn)
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
            # Take the first token safely to avoid IndexError on empty text.
            def _first_token(text: str) -> str:
                parts = text.split()
                return parts[0] if parts else ""

            raw_dl = app.driver.find_element(By.XPATH, f"{base_xp}/tr[3]/td[3]/strong").text
            download = _first_token(raw_dl)
            raw_ul = app.driver.find_element(By.XPATH, f"{base_xp}/tr[4]/td[3]/strong").text
            upload = _first_token(raw_ul)
            raw_lat = app.driver.find_element(By.XPATH, f"{base_xp}/tr[5]/td[3]/strong").text
            latency = _first_token(raw_lat)
            raw_retr = app.driver.find_element(By.XPATH, f"{base_xp}/tr[6]/td[3]/strong").text
            retrans = raw_retr.replace("%", "").strip()

            logger.debug(f"mlab Result: {download=} {upload=} {latency=} {retrans=}")

            if not any(c.isdigit() for c in download):
                logger.error("mlab: Invalid download value; skipping send.")
                app.take_snapshot("mlab_error_parse")
                return

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
            app.send_results(data)

        except Exception as e:
            logger.error(f"mlab: Error extracting results: {e}")
            return

    except Exception as e:
        logger.error(f"mlab Error: {e}")
    finally:
        app.take_snapshot("mlab")
