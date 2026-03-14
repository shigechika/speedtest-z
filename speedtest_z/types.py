"""Type definitions for speedtest-z."""

from __future__ import annotations

from typing import Protocol, TypedDict


class ZabbixItem(TypedDict):
    """A single Zabbix trapper item."""

    host: str
    key: str
    value: str


class MetricSender(Protocol):
    """Protocol for metric backends (SenderManager, OutputCollector)."""

    def send(self, data_list: list[dict[str, str]]) -> None:
        """Send measurement results."""
        ...

    def close(self) -> None:
        """Shut down the backend."""
        ...
