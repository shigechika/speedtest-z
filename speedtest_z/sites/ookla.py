"""Site runner for Ookla Speedtest."""

from __future__ import annotations

import contextlib
import logging
import re
import time
from typing import TYPE_CHECKING, Literal

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver
    from selenium.webdriver.remote.webelement import WebElement

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


def _select_server(app: SpeedtestZ) -> None:
    """Pin the measurement server on the redesigned UI (best effort).

    Flow verified in a human-driven browser 2026-07-18: the pre-test page has
    a "Change Server" <button> (the pre-2026 LINK_TEXT selector matched only
    <a> tags), which opens a [role="dialog"] with a single text input; result
    rows are div[role="button"] list items and the dialog closes on
    selection. Caveat: under automated (Selenium) Chrome the pre-test server
    discovery has been observed to stall ("Finding optimal server..."), in
    which case the button never renders and this helper times out after 15s.
    Any failure falls through to the auto-selected server.
    """
    server = app.ookla_server
    if not server:
        return

    def _visible_change_button(driver: WebDriver) -> WebElement | Literal[False]:
        # The page renders two "Change Server" buttons (responsive variants);
        # element_to_be_clickable would latch onto the first match even when
        # it is the hidden one, so pick whichever is actually displayed.
        for btn in driver.find_elements(By.XPATH, "//button[normalize-space()='Change Server']"):
            if btn.is_displayed() and btn.is_enabled():
                return btn
        return False

    try:
        # The button appears only after "Finding optimal server..." resolves
        change_btn = WebDriverWait(app.driver, 15).until(_visible_change_button)
        change_btn.click()
        dialog = WebDriverWait(app.driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, '[role="dialog"]'))
        )

        # The dialog header shows the currently selected server
        if server.lower() in dialog.text[:150].lower():
            logger.info(f"ookla: Server already selected ({server}).")
            app.driver.switch_to.active_element.send_keys(Keys.ESCAPE)
            return

        search_box = dialog.find_element(By.CSS_SELECTOR, 'input[type="text"]')
        search_box.send_keys(server)

        def _server_rows(driver: WebDriver) -> list[WebElement] | Literal[False]:
            # Rows are div[role=button] list items; icon-only buttons (close,
            # Select Automatically) are <button> tags or have no text
            rows = [
                r
                for r in dialog.find_elements(By.CSS_SELECTOR, 'div[role="button"]')
                if (r.text or "").strip()
            ]
            return rows or False

        rows = WebDriverWait(app.driver, 10).until(_server_rows)
        target = next((r for r in rows if server.lower() in r.text.lower()), rows[0])
        label = target.text.splitlines()[0] if target.text else server
        target.click()
        logger.info(f"ookla: Server selected ({label})")
    except Exception as e:
        logger.warning(f"ookla: Server selection failed; using auto-selected server: {e}")
        # Close a possibly-open dialog so it cannot block the GO button
        with contextlib.suppress(Exception):
            app.driver.switch_to.active_element.send_keys(Keys.ESCAPE)


def run_ookla(app: SpeedtestZ) -> None:
    """Run Ookla Speedtest (speedtest.net)."""
    if not app._should_run("ookla"):
        return

    for attempt in range(app.MAX_RETRIES):
        try:
            logger.info(f"ookla: OPEN (Attempt {attempt + 1}/{app.MAX_RETRIES})")

            # On retries, navigate back to the top page: a finished attempt
            # leaves the browser on a /result/<id> URL where refresh() would
            # not offer a new test. A sustained reload failure (after
            # _load_with_retry's own retries) aborts the runner instead of
            # burning the remaining attempts on an unreachable page (#41).
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

            # Server selection (best effort; falls through to the
            # auto-selected server on any failure)
            if app.ookla_server is not None:
                _select_server(app)

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
