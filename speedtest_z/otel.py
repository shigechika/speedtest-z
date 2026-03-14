"""OpenTelemetry (OTLP) metrics sender."""

from __future__ import annotations

import logging
from typing import Any

from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

logger = logging.getLogger("speedtest-z")


class OtelSender:
    """OTLP metrics sender using OpenTelemetry SDK."""

    def __init__(self, endpoint: str, headers: dict[str, str], host: str) -> None:
        """Initialize OtelSender with OTLP exporter and MeterProvider."""
        self.host = host
        # endpoint をプログラムで渡す場合は /v1/metrics まで含める必要がある
        # （環境変数 OTEL_EXPORTER_OTLP_ENDPOINT の場合のみ SDK が自動付加）
        if not endpoint.endswith("/v1/metrics"):
            endpoint = endpoint.rstrip("/") + "/v1/metrics"
        self.exporter = OTLPMetricExporter(
            endpoint=endpoint,
            headers=headers,
        )
        self.resource = Resource.create(
            {
                "service.name": "speedtest-z",
                "host.name": host,
            }
        )
        reader = PeriodicExportingMetricReader(
            self.exporter,
            export_interval_millis=60000,  # 手動 flush するので長めに設定
        )
        self.provider = MeterProvider(resource=self.resource, metric_readers=[reader])
        self.meter = self.provider.get_meter("speedtest-z")
        # 作成済み gauge をキャッシュ
        self._gauges: dict[str, Any] = {}

    def send(self, data_list: list[dict[str, str]]) -> None:
        """Send metrics via OTLP."""
        for item in data_list:
            key = item.get("key", "")
            value_str = item.get("value", "")
            try:
                value = float(value_str)
            except (ValueError, TypeError):
                logger.debug(f"OTel skip: {key} = {value_str} (non-numeric)")
                continue

            parts = key.split(".", 1)
            if len(parts) != 2:
                continue
            site, metric = parts
            metric_name = f"speedtest_{metric.replace('-', '_')}"

            # gauge を作成（同名なら SDK が内部でキャッシュ）
            if metric_name not in self._gauges:
                self._gauges[metric_name] = self.meter.create_gauge(metric_name)

            host = item.get("host", self.host)
            self._gauges[metric_name].set(value, {"site": site, "host": host})

        # 即時エクスポート
        self.provider.force_flush()

    def shutdown(self) -> None:
        """Shutdown the MeterProvider."""
        self.provider.shutdown()
