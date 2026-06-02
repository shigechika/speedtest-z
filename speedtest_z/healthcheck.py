"""Site URL health check (--check)."""

from __future__ import annotations

import urllib.error
import urllib.request

from speedtest_z.sites.boxtest import URL as BOXTEST_URL
from speedtest_z.sites.cloudflare import URL as CLOUDFLARE_URL
from speedtest_z.sites.google import URL as GOOGLE_URL
from speedtest_z.sites.inonius import URL as INONIUS_URL
from speedtest_z.sites.mlab import URL as MLAB_URL
from speedtest_z.sites.netflix import URL as NETFLIX_URL
from speedtest_z.sites.ookla import URL as OOKLA_URL
from speedtest_z.sites.usen import URL as USEN_URL

SITE_URLS: dict[str, str] = {
    "cloudflare": CLOUDFLARE_URL,
    "netflix": NETFLIX_URL,
    "google": GOOGLE_URL,
    "ookla": OOKLA_URL,
    "boxtest": BOXTEST_URL,
    "mlab": MLAB_URL,
    "usen": USEN_URL,
    "inonius": INONIUS_URL,
}


def check_sites(sites: list[str] | None = None) -> int:
    """Check HTTP reachability of speed test sites.

    Sends an HTTP HEAD request to each site URL (falls back to GET on
    405 Method Not Allowed).  Prints a summary table and returns 0 if
    all sites are reachable, 1 otherwise.

    Args:
        sites: List of site names to check.  If None or empty, all sites
               are checked.

    Returns:
        Exit code: 0 = all OK, 1 = one or more failures.
    """
    targets = sites if sites else list(SITE_URLS.keys())
    has_failure = False

    print("Site Health Check:")
    for site in targets:
        url = SITE_URLS.get(site)
        if not url:
            print(f"  {site:<12}  ---  Unknown site")
            has_failure = True
            continue

        status, reason = _check_url(url)
        ok = 200 <= status < 400
        label = "OK" if ok else "FAIL"
        if not ok:
            has_failure = True
            print(f"  {site:<12}  {status}  {label}  {reason}")
        else:
            print(f"  {site:<12}  {status}  {label}")

    return 1 if has_failure else 0


def _check_url(url: str, timeout: int = 10) -> tuple[int, str]:
    """Send HEAD request to URL, fallback to GET on 405.

    Returns:
        Tuple of (status_code, reason).  On network errors returns
        (0, error_description).
    """
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method)
            req.add_header("User-Agent", "speedtest-z/healthcheck")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return (resp.status, resp.reason)
        except urllib.error.HTTPError as e:
            # Some servers reject HEAD with 405 (Method Not Allowed) or
            # 501 (Not Implemented); fall back to GET in both cases.
            if e.code in (405, 501) and method == "HEAD":
                continue
            return (e.code, str(e.reason))
        except Exception as e:
            return (0, str(e))

    return (0, "Unknown error")
