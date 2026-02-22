"""Output formatters for JSON/CSV output (--output)."""

from __future__ import annotations

import csv
import io
import json
import sys
from datetime import datetime, timezone


class OutputCollector:
    """Collect measurement results and flush them in the requested format.

    Used when ``--output json`` or ``--output csv`` is specified.  Each
    site runner calls ``app.send_results(data)`` as before; the CLI
    layer intercepts this and calls :meth:`add` instead of actually
    sending to backends.

    Args:
        fmt: Output format (``"json"`` or ``"csv"``).
    """

    def __init__(self, fmt: str) -> None:
        self.fmt = fmt
        self._records: list[dict[str, str]] = []

    def add(self, data_list: list[dict[str, str]]) -> None:
        """Buffer a batch of Zabbix-style dicts."""
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for item in data_list:
            self._records.append(
                {
                    "timestamp": ts,
                    "host": item.get("host", ""),
                    "key": item["key"],
                    "value": item["value"],
                }
            )

    def flush(self) -> None:
        """Write all buffered records to stdout."""
        if self.fmt == "json":
            self._flush_json()
        elif self.fmt == "csv":
            self._flush_csv()

    def _flush_json(self) -> None:
        """Output as JSON array."""
        json.dump(self._records, sys.stdout, ensure_ascii=False, indent=2)
        print()  # 末尾改行

    def _flush_csv(self) -> None:
        """Output as CSV with header."""
        if not self._records:
            return
        fieldnames = ["timestamp", "host", "key", "value"]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(self._records)
        sys.stdout.write(buf.getvalue())
