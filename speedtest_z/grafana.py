"""Grafana Cloud Prometheus Remote Write sender."""

from __future__ import annotations

import base64
import logging
import struct
import time
import urllib.error
import urllib.request

logger = logging.getLogger("speedtest-z")


# --- Manual Protobuf encoder (no protobuf package required) ---
# Prometheus Remote Write proto definitions:
#   WriteRequest { repeated TimeSeries timeseries = 1; }
#   TimeSeries   { repeated Label labels = 1; repeated Sample samples = 2; }
#   Label        { string name = 1; string value = 2; }
#   Sample       { double value = 1; int64 timestamp = 2; }


def _encode_varint(value: int) -> bytes:
    """Encode an integer as a protobuf varint."""
    result = []
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)


def _encode_bytes(field_number: int, data: bytes) -> bytes:
    """Encode a protobuf length-delimited field (wire type 2)."""
    tag = _encode_varint((field_number << 3) | 2)
    return tag + _encode_varint(len(data)) + data


def _encode_string(field_number: int, value: str) -> bytes:
    """Encode a protobuf string field."""
    return _encode_bytes(field_number, value.encode("utf-8"))


def _encode_double(field_number: int, value: float) -> bytes:
    """Encode a protobuf double field (wire type 1)."""
    tag = _encode_varint((field_number << 3) | 1)
    return tag + struct.pack("<d", value)


def _encode_int64(field_number: int, value: int) -> bytes:
    """Encode a protobuf int64 field (wire type 0)."""
    tag = _encode_varint((field_number << 3) | 0)
    return tag + _encode_varint(value)


def encode_label(name: str, value: str) -> bytes:
    """Encode Label { string name = 1; string value = 2; }."""
    return _encode_string(1, name) + _encode_string(2, value)


def encode_sample(value: float, timestamp_ms: int) -> bytes:
    """Encode Sample { double value = 1; int64 timestamp = 2; }."""
    return _encode_double(1, value) + _encode_int64(2, timestamp_ms)


def encode_timeseries(labels: list[tuple[str, str]], value: float, timestamp_ms: int) -> bytes:
    """Encode TimeSeries { repeated Label labels = 1; repeated Sample samples = 2; }."""
    data = b""
    for name, val in labels:
        data += _encode_bytes(1, encode_label(name, val))
    data += _encode_bytes(2, encode_sample(value, timestamp_ms))
    return data


def encode_write_request(timeseries_list: list[bytes]) -> bytes:
    """Encode WriteRequest { repeated TimeSeries timeseries = 1; }."""
    data = b""
    for ts in timeseries_list:
        data += _encode_bytes(1, ts)
    return data


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuse to follow HTTP redirects.

    Prevents the ``Authorization`` header (and the metric payload) from being
    forwarded to a redirect target.  A redirect from a Prometheus Remote Write
    endpoint is anomalous, so it is surfaced as an :class:`~urllib.error.HTTPError`.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


class GrafanaSender:
    """Grafana Cloud Prometheus Remote Write sender."""

    # A single push completes within seconds, so use a short cap to avoid hangs.
    TIMEOUT = 30

    def __init__(self, url: str, username: str, token: str) -> None:
        """Initialize with Grafana Cloud credentials."""
        self.url = url
        self.username = username
        self.token = token

    def send(self, data_list: list[dict[str, str]]) -> None:
        """Send measurement results to Grafana Cloud.

        Accepts the same data_list format as send_results().
        Non-numeric values are skipped (e.g. server-locations, POP).
        Keys are split into site.metric -> __name__=speedtest_<metric>, site=<site>.
        """
        import cramjam

        timeseries = []
        timestamp_ms = int(time.time() * 1000)

        for item in data_list:
            key = item.get("key", "")
            value_str = item.get("value", "")

            # skip non-numeric values (server-locations, POP, etc.)
            try:
                value = float(value_str)
            except (ValueError, TypeError):
                logger.debug(f"Grafana skip: {key} = {value_str} (non-numeric)")
                continue

            # split key into site and metric (e.g. cloudflare.download)
            parts = key.split(".", 1)
            if len(parts) != 2:
                continue
            site, metric = parts

            metric_name = f"speedtest_{metric.replace('-', '_')}"
            labels = [
                ("__name__", metric_name),
                ("site", site),
                ("host", item.get("host", "")),
            ]
            timeseries.append(encode_timeseries(labels, value, timestamp_ms))

        if not timeseries:
            logger.debug("Grafana: no numeric metrics to send")
            return

        write_request = encode_write_request(timeseries)
        compressed = bytes(cramjam.snappy.compress_raw(write_request))

        req = urllib.request.Request(self.url, data=compressed, method="POST")
        req.add_header("Content-Type", "application/x-protobuf")
        req.add_header("Content-Encoding", "snappy")
        req.add_header("X-Prometheus-Remote-Write-Version", "0.1.0")

        credentials = base64.b64encode(f"{self.username}:{self.token}".encode()).decode()
        # An unredirected header is not forwarded on redirects, so the
        # credentials never leak to a redirect target (defense in depth with
        # the no-redirect opener below).
        req.add_unredirected_header("Authorization", f"Basic {credentials}")

        opener = urllib.request.build_opener(_NoRedirectHandler)
        try:
            with opener.open(req, timeout=self.TIMEOUT) as resp:
                logger.info(f"Grafana push OK: {resp.status} {resp.reason}")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            logger.error(f"Grafana push failed: {e.code} {e.reason} — {body}")
            raise
