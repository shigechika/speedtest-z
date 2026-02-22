"""Type definitions for speedtest-z."""

from __future__ import annotations

from typing import TypedDict


class ZabbixItem(TypedDict):
    """A single Zabbix trapper item."""

    host: str
    key: str
    value: str
