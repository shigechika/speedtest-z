"""Site runners for speedtest-z.

Each site module exposes a ``run_<site>(app)`` function that drives
a browser-based speed test and sends results to Zabbix.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from speedtest_z.runner import SpeedtestZ

# 利用可能なテストサイト一覧
AVAILABLE_SITES = [
    "cloudflare",
    "netflix",
    "google",
    "ookla",
    "boxtest",
    "mlab",
    "usen",
    "inonius",
]


def get_site_runners() -> dict[str, Callable[[SpeedtestZ], None]]:
    """Return a mapping of site name to runner function.

    Imports are deferred to avoid circular dependencies and to keep
    start-up lightweight when only a subset of sites is requested.
    """
    from speedtest_z.sites.boxtest import run_boxtest
    from speedtest_z.sites.cloudflare import run_cloudflare
    from speedtest_z.sites.google import run_google
    from speedtest_z.sites.inonius import run_inonius
    from speedtest_z.sites.mlab import run_mlab
    from speedtest_z.sites.netflix import run_netflix
    from speedtest_z.sites.ookla import run_ookla
    from speedtest_z.sites.usen import run_usen

    return {
        "cloudflare": run_cloudflare,
        "netflix": run_netflix,
        "google": run_google,
        "ookla": run_ookla,
        "boxtest": run_boxtest,
        "mlab": run_mlab,
        "usen": run_usen,
        "inonius": run_inonius,
    }
