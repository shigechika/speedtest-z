"""speedtest-z: Selenium ベースの複数サイト速度テスト + Zabbix 連携ツール"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("speedtest-z")
except PackageNotFoundError:
    __version__ = "0.0.0"
