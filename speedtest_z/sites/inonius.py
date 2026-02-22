"""Site runner for iNonius Speed Test."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

if TYPE_CHECKING:
    from speedtest_z.runner import SpeedtestZ

logger = logging.getLogger("speedtest-z")

URL = "https://inonius.net/speedtest/"


def _inonius_fallback_start(app: SpeedtestZ) -> bool:
    """Attempt to start iNonius test when consent dialog was skipped.

    When cookies remember consent, the dialog may not appear and the test
    may start automatically or require a manual start button click.
    Returns True if the test appears to be running, False otherwise.
    """
    try:
        # dialog なしでテストが自動開始されたか確認
        # Download/Upload の数値やアニメーションが表示されていれば進行中
        WebDriverWait(app.driver, 10).until(
            lambda d: (
                d.find_elements(By.CSS_SELECTOR, "astro-island > div")
                and not d.find_elements(By.CSS_SELECTOR, "dialog[open]")
            )
        )
        logger.info("inonius: Test already running (cookie consent)")
        return True
    except TimeoutException:
        logger.error("inonius: Could not start test (no dialog, no auto-start)")
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
            # --yes: 同意ダイアログを自動クリック（同意兼スタート）
            try:
                start_btn = WebDriverWait(app.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, start_xpath))
                )
                start_btn.click()
                logger.info("inonius: Consent accepted and started (auto)")
            except TimeoutException:
                # Cookie で dialog が出ない → フォールバック
                if not _inonius_fallback_start(app):
                    return
        else:
            # --yes なし: ユーザ操作を待つか、Cookie で dialog が出ない場合のフォールバック
            try:
                dialog = WebDriverWait(app.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "dialog"))
                )
                # dialog が表示されたらユーザがクリックして閉じるのを待つ
                logger.info("inonius: Waiting for user to accept consent dialog...")
                WebDriverWait(app.driver, 120).until(lambda d: not dialog.is_displayed())
                logger.info("inonius: Dialog closed by user")
            except TimeoutException:
                # dialog が出ない（Cookie で記憶済み）→ フォールバック
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
                    val = val.split()[-1]
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
