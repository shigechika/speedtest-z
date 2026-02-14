"""speedtest-z: Automated multi-site speed test runner.

Runs speed tests on 8 major sites using a web browser (Selenium)
and sends results to Zabbix as trapper items.

Supported sites:
    cloudflare  - Cloudflare Speed Test
    netflix     - Netflix fast.com
    google      - Google Fiber Speedtest
    ookla       - Ookla Speedtest
    boxtest     - Box-test
    mlab        - M-Lab Speed Test
    usen        - USEN GATE 02
    inonius     - iNonius Speedtest

Quick start::

    $ pip install speedtest-z
    $ speedtest-z --dry-run
    $ speedtest-z --man

See Also:
    https://github.com/shigechika/speedtest-z
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("speedtest-z")
except PackageNotFoundError:
    __version__ = "0.0.0"
