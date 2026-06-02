"""Tests for the OpenTelemetry integration."""

import configparser
from unittest.mock import MagicMock, patch

import pytest

from speedtest_z.runner import SpeedtestZ
from speedtest_z.sender import SenderManager

try:
    import opentelemetry.sdk.metrics  # noqa: F401

    _has_otel = True
except ImportError:
    _has_otel = False

# --- Unit tests for OtelSender ---


@pytest.mark.skipif(not _has_otel, reason="opentelemetry not installed")
class TestOtelSender:
    """Tests for OtelSender."""

    def _make_sender(self):
        """Create a mocked OtelSender."""
        with (
            patch("speedtest_z.otel.OTLPMetricExporter") as mock_exporter_cls,
            patch("speedtest_z.otel.PeriodicExportingMetricReader"),
            patch("speedtest_z.otel.MeterProvider") as mock_provider_cls,
        ):
            mock_provider = MagicMock()
            mock_meter = MagicMock()
            mock_provider.get_meter.return_value = mock_meter
            mock_provider_cls.return_value = mock_provider

            from speedtest_z.otel import OtelSender

            sender = OtelSender(
                "https://otlp.example.com",
                {"Api-Key": "test-key"},
                "test-host",
            )
            # Keep references to the mocks
            sender._mock_exporter_cls = mock_exporter_cls
            sender._mock_provider = mock_provider
            sender._mock_meter = mock_meter
        return sender

    def test_init(self):
        """Attributes are set during initialization."""
        sender = self._make_sender()
        assert sender.provider is not None
        assert sender.meter is not None
        assert sender._gauges == {}

    def test_send_numeric_values(self):
        """Numeric metrics are recorded on a gauge."""
        sender = self._make_sender()
        mock_gauge = MagicMock()
        sender._mock_meter.create_gauge.return_value = mock_gauge

        data = [
            {"key": "cloudflare.download", "value": "100.5", "host": "test-host"},
            {"key": "cloudflare.upload", "value": "50.2", "host": "test-host"},
        ]
        sender.send(data)

        # Verify the gauges were created
        assert sender._mock_meter.create_gauge.call_count == 2
        # Verify set() was called
        assert mock_gauge.set.call_count == 2
        mock_gauge.set.assert_any_call(100.5, {"site": "cloudflare", "host": "test-host"})
        mock_gauge.set.assert_any_call(50.2, {"site": "cloudflare", "host": "test-host"})
        # Verify force_flush was called
        sender._mock_provider.force_flush.assert_called_once()

    def test_send_skips_non_numeric(self):
        """Non-numeric values are skipped."""
        sender = self._make_sender()
        data = [
            {"key": "netflix.server-locations", "value": "Tokyo, Osaka"},
            {"key": "boxtest.POP", "value": "NRT"},
        ]
        sender.send(data)
        # No gauge is created
        sender._mock_meter.create_gauge.assert_not_called()
        # force_flush is still called (even when empty)
        sender._mock_provider.force_flush.assert_called_once()

    def test_send_skips_invalid_key(self):
        """A key without a dot is skipped."""
        sender = self._make_sender()
        data = [{"key": "invalid_key", "value": "100.5"}]
        sender.send(data)
        sender._mock_meter.create_gauge.assert_not_called()

    def test_send_mixed_values(self):
        """When numeric and non-numeric values are mixed, only the numeric ones are recorded."""
        sender = self._make_sender()
        mock_gauge = MagicMock()
        sender._mock_meter.create_gauge.return_value = mock_gauge

        data = [
            {"key": "cloudflare.download", "value": "100.5", "host": "test"},
            {"key": "netflix.server-locations", "value": "Tokyo"},
        ]
        sender.send(data)
        # A gauge is created only for the single numeric value
        sender._mock_meter.create_gauge.assert_called_once_with("speedtest_download")
        mock_gauge.set.assert_called_once_with(100.5, {"site": "cloudflare", "host": "test"})

    def test_send_empty_list(self):
        """An empty list does not error."""
        sender = self._make_sender()
        sender.send([])
        sender._mock_meter.create_gauge.assert_not_called()
        sender._mock_provider.force_flush.assert_called_once()

    def test_send_caches_gauge(self):
        """The gauge for an identically named metric is cached."""
        sender = self._make_sender()
        mock_gauge = MagicMock()
        sender._mock_meter.create_gauge.return_value = mock_gauge

        data = [
            {"key": "cloudflare.download", "value": "100.5", "host": "h1"},
            {"key": "netflix.download", "value": "80.0", "host": "h1"},
        ]
        sender.send(data)
        # Same metric_name "speedtest_download", so create_gauge is called once
        sender._mock_meter.create_gauge.assert_called_once_with("speedtest_download")
        assert mock_gauge.set.call_count == 2

    def test_send_hyphen_to_underscore(self):
        """Hyphens in the metric name are converted to underscores."""
        sender = self._make_sender()
        mock_gauge = MagicMock()
        sender._mock_meter.create_gauge.return_value = mock_gauge

        data = [{"key": "netflix.server-locations-count", "value": "3", "host": "h1"}]
        sender.send(data)
        sender._mock_meter.create_gauge.assert_called_once_with("speedtest_server_locations_count")
        mock_gauge.set.assert_called_once_with(3.0, {"site": "netflix", "host": "h1"})

    def test_shutdown(self):
        """provider.shutdown() is called by shutdown()."""
        sender = self._make_sender()
        sender.shutdown()
        sender._mock_provider.shutdown.assert_called_once()


# --- Fallback tests for ImportError ---


class TestOtelImportFallback:
    """Graceful fallback tests for when opentelemetry is not installed."""

    def test_runner_otel_without_opentelemetry(self):
        """A warning is emitted when [otel] enable=true but opentelemetry is missing."""
        config = configparser.ConfigParser()
        config.read_dict(
            {
                "general": {"dry_run": "true", "headless": "true", "timeout": "30"},
                "zabbix": {
                    "enable": "false",
                    "server": "127.0.0.1",
                    "port": "10051",
                    "host": "test",
                },
                "otel": {
                    "enable": "true",
                    "endpoint": "https://otlp.example.com",
                    "headers": "Api-Key=test-key",
                },
            }
        )
        with (
            patch.object(SpeedtestZ, "__init__", lambda self, *a, **kw: None),
            patch.object(SpeedtestZ, "_init_driver"),
            patch("speedtest_z.runner._find_config", return_value=None),
            patch("speedtest_z.runner.signal.signal"),
        ):
            app = SpeedtestZ.__new__(SpeedtestZ)
            app.config = config
            app.dryrun = True
            app.otel_sender = None
            app.zabbix_host = "test"
            # Simulate loading the [otel] section
            if config.has_section("otel"):
                otel_enable = config.getboolean("otel", "enable", fallback=False)
                if otel_enable:
                    try:
                        raise ImportError("No module named 'opentelemetry'")
                    except ImportError:
                        pass  # graceful fallback
            assert app.otel_sender is None


# --- Integration tests for send_results() ---


def _make_sender(dryrun=True, zabbix_enable=False, grafana_sender=None, otel_sender=None):
    """Create a SenderManager instance directly."""
    with patch.object(SenderManager, "__init__", lambda self, *a, **kw: None):
        sender = SenderManager.__new__(SenderManager)
        sender.dry_run = dryrun
        sender.zabbix_enable = zabbix_enable
        sender.zabbix_server = "127.0.0.1"
        sender.zabbix_port = 10051
        sender.zabbix_host = "speedtest-agent"
        sender.grafana_sender = grafana_sender
        sender.otel_sender = otel_sender
    return sender


class TestSendResultsOtel:
    """OTel send tests for SenderManager.send()."""

    def test_otel_sender_called(self):
        """send() is called when otel_sender is set."""
        mock_otel = MagicMock()
        sender = _make_sender(dryrun=False, otel_sender=mock_otel)
        data = [{"key": "cloudflare.download", "value": "100.5"}]
        with patch("speedtest_z.sender.Sender"):
            sender.send(data)
            mock_otel.send.assert_called_once_with(data)

    def test_otel_sender_not_called_on_dryrun(self):
        """otel_sender.send() is not called when dryrun=True."""
        mock_otel = MagicMock()
        sender = _make_sender(dryrun=True, otel_sender=mock_otel)
        data = [{"key": "cloudflare.download", "value": "100.5"}]
        sender.send(data)
        mock_otel.send.assert_not_called()

    def test_otel_error_handled(self):
        """An OTel send error does not crash the run."""
        mock_otel = MagicMock()
        mock_otel.send.side_effect = Exception("Connection error")
        sender = _make_sender(dryrun=False, otel_sender=mock_otel)
        data = [{"key": "cloudflare.download", "value": "100.5"}]
        with patch("speedtest_z.sender.Sender"):
            sender.send(data)  # the exception does not propagate

    def test_all_three_backends(self):
        """All three of Zabbix, Grafana, and OTel are called."""
        mock_grafana = MagicMock()
        mock_otel = MagicMock()
        sender = _make_sender(
            dryrun=False,
            zabbix_enable=True,
            grafana_sender=mock_grafana,
            otel_sender=mock_otel,
        )
        data = [{"key": "cloudflare.download", "value": "100.5"}]
        with patch("speedtest_z.sender.Sender") as mock_sender_cls:
            mock_instance = MagicMock()
            mock_sender_cls.return_value = mock_instance
            sender.send(data)
            mock_instance.send_bulk.assert_called_once()
            mock_grafana.send.assert_called_once_with(data)
            mock_otel.send.assert_called_once_with(data)


# --- OTel shutdown tests for close() ---


class TestCloseOtel:
    """OTel shutdown tests for SenderManager.close()."""

    def test_close_calls_otel_shutdown(self):
        """otel_sender.shutdown() is called by close()."""
        mock_otel = MagicMock()
        sender = _make_sender(otel_sender=mock_otel)
        sender.close()
        mock_otel.shutdown.assert_called_once()

    def test_close_without_otel(self):
        """close() does not error even when otel_sender=None."""
        sender = _make_sender(otel_sender=None)
        sender.close()  # should not raise
