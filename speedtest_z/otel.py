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
        # When passing the endpoint programmatically, it must include /v1/metrics
        # (the SDK only appends it automatically for the OTEL_EXPORTER_OTLP_ENDPOINT env var).
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
            export_interval_millis=60000,  # set long since we flush manually
        )
        self.provider = MeterProvider(resource=self.resource, metric_readers=[reader])
        self.meter = self.provider.get_meter("speedtest-z")
        # cache created gauges
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

            # create the gauge (the SDK caches it internally if the name matches)
            if metric_name not in self._gauges:
                self._gauges[metric_name] = self.meter.create_gauge(metric_name)

            host = item.get("host", self.host)
            self._gauges[metric_name].set(value, {"site": site, "host": host})

        # export immediately
        self.provider.force_flush()

    def shutdown(self) -> None:
        """Shutdown the MeterProvider."""
        self.provider.shutdown()
