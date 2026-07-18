"""Site runner for Ookla Speedtest."""

from __future__ import annotations

import logging
import re
import time
from typing import TYPE_CHECKING

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

if TYPE_CHECKING:
    from speedtest_z.runner import SpeedtestZ

logger = logging.getLogger("speedtest-z")

URL = "https://www.speedtest.net/"

# The redesigned UI (React/MUI, observed 2026-07) has no stable ids/classes on
# the GO button; the aria-label is the only semantic hook. The trailing "i"
# makes the match case-insensitive so a cosmetic case change cannot break it.
START_BUTTON = (By.CSS_SELECTOR, 'button[aria-label^="start speed test" i]')

# Result values render as <h3 class="... font-mono ..."> inside a small
# labelled container, and latency values as bare numeric spans. The utility
# (Tailwind) class names carry no semantics, so extract everything in one
# JavaScript pass. Each h3 is classified by its NEAREST labelled ancestor
# ("Download Mbps 92.98" / "Upload Mbps 87.07"); a wider ancestor whose text
# contains both labels is ambiguous and must be skipped, otherwise the
# download value would also be reported as upload.
_EXTRACT_RESULTS_JS = """
const results = {download: null, upload: null};
for (const h of document.querySelectorAll('h3.font-mono')) {
  let box = h.parentElement;
  for (let i = 0; i < 4 && box; i++) {
    const t = (box.textContent || '').toLowerCase();
    if (t.length < 60 && (t.includes('download') || t.includes('upload'))) {
      if (!(t.includes('download') && t.includes('upload'))) {
        const key = t.includes('download') ? 'download' : 'upload';
        if (results[key] === null) results[key] = h.textContent.trim();
      }
      break;
    }
    box = box.parentElement;
  }
}
const isNum = (t) => /^[0-9]+(\\.[0-9]+)?$/.test(t);
let ping = null;
// The three latency rows each carry an icon labelled "Idle Latency" /
// "Download Latency" / "Upload Latency"; anchor idle ping to its icon so a
// layout reorder cannot swap in a different latency value.
const idleIcon = document.querySelector('[aria-label="idle latency" i]');
if (idleIcon && idleIcon.parentElement) {
  const span = [...idleIcon.parentElement.querySelectorAll('span')]
    .find(s => isNum((s.textContent || '').trim()));
  if (span) ping = span.textContent.trim();
}
if (ping === null) {
  const pings = [...document.querySelectorAll('span[class*="min-w"]')]
    .map(e => (e.textContent || '').trim())
    .filter(isNum);
  ping = pings[0] || null;
}
return {download: results.download, upload: results.upload, ping: ping};
"""


def _clean_number(text: str) -> str:
    """Normalize a scraped value to a bare numeric string.

    Strips thousands separators and unit suffixes ("1,053.9" -> "1053.9",
    "92.98 Mbps" -> "92.98"); returns "" when no numeric token remains, so
    callers can treat the value as a parse failure. Zabbix items are FLOAT
    and would reject a comma- or unit-decorated string.
    """
    tokens = text.replace(",", "").split()
    token = tokens[0] if tokens else ""
    return token if re.fullmatch(r"[0-9]+(\.[0-9]+)?", token) else ""


def run_ookla(app: SpeedtestZ) -> None:
    """Run Ookla Speedtest (speedtest.net)."""
    if not app._should_run("ookla"):
        return

    for attempt in range(app.MAX_RETRIES):
        try:
            logger.info(f"ookla: OPEN (Attempt {attempt + 1}/{app.MAX_RETRIES})")

            # On retries, navigate back to the top page: a finished attempt
            # leaves the browser on a /result/<id> URL where refresh() would
            # not offer a new test.
            if attempt > 0:
                logger.info("ookla: Reloading page...")
            if not app._load_with_retry(URL):
                return
            if attempt > 0:
                time.sleep(5)

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
                # If a banner is shown, wait for the user to click "Continue"
                try:
                    banner = WebDriverWait(app.driver, 5).until(
                        EC.visibility_of_element_located((By.ID, "onetrust-banner-sdk"))
                    )
                    logger.info("ookla: Waiting for user to accept privacy banner...")
                    WebDriverWait(app.driver, 120).until(EC.invisibility_of_element(banner))
                    logger.info("ookla: Privacy banner dismissed by user")
                except TimeoutException:
                    logger.debug("ookla: Privacy banner not found or not dismissed")

            # Server Selection (best effort: written for the pre-2026 UI; the
            # redesigned UI keeps a "Change Server" link but the surrounding
            # selectors are unverified. Failures fall through to the default
            # auto-selected server.)
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
                start_btn = app.wait.until(EC.element_to_be_clickable(START_BUTTON))
                start_btn.click()
                logger.info("ookla: START")
            except Exception as e:
                logger.warning(f"ookla: Start button error: {e}")
                continue

            # A finished test navigates to /result/<id>; an error popup or a
            # stalled test never does, so the timeout below covers both.
            try:
                WebDriverWait(app.driver, 90).until(lambda d: "/result/" in d.current_url)
            except TimeoutException:
                logger.error("ookla: Timeout waiting for results.")
                app.take_snapshot(f"ookla_timeout_{attempt + 1}")
                continue

            logger.info("ookla: COMPLETED")
            time.sleep(2)

            result = app.driver.execute_script(_EXTRACT_RESULTS_JS) or {}
            download = _clean_number(result.get("download") or "")
            upload = _clean_number(result.get("upload") or "")
            ping = _clean_number(result.get("ping") or "")

            logger.debug(f"ookla Result: {download=} {upload=} {ping=}")

            # Both throughput values must parse, or the attempt is retried —
            # sending a partial result would hide an extraction regression.
            if not download or not upload:
                logger.error("ookla: Invalid download/upload value; retrying.")
                app.take_snapshot(f"ookla_error_parse_{attempt + 1}")
                continue

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
            ]
            if ping:
                data.append(
                    {
                        "host": app.zabbix_host,
                        "key": "ookla.ping",
                        "value": ping,
                    }
                )
            else:
                # The ping span heuristic is weaker than the labelled h3s;
                # do not fail a good throughput measurement over it.
                logger.warning("ookla: ping value missing; sending download/upload only.")
            app.send_results(data)
            app.take_snapshot("ookla")
            return

        except Exception as e:
            logger.error(f"ookla Error (Attempt {attempt + 1}): {e}")
            app.take_snapshot(f"ookla_exception_{attempt + 1}")
            time.sleep(3)

    logger.error("ookla: Failed after all retries.")
