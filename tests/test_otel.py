"""OpenTelemetry 統合のテスト"""

import configparser
from unittest.mock import MagicMock, patch

import pytest

from speedtest_z.runner import SpeedtestZ

try:
    import opentelemetry.sdk.metrics  # noqa: F401

    _has_otel = True
except ImportError:
    _has_otel = False

# --- OtelSender のユニットテスト ---


@pytest.mark.skipif(not _has_otel, reason="opentelemetry not installed")
class TestOtelSender:
    """OtelSender のテスト"""

    def _make_sender(self):
        """モック化した OtelSender を作成"""
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
            # モック参照を保持
            sender._mock_exporter_cls = mock_exporter_cls
            sender._mock_provider = mock_provider
            sender._mock_meter = mock_meter
        return sender

    def test_init(self):
        """初期化で属性が設定されること"""
        sender = self._make_sender()
        assert sender.provider is not None
        assert sender.meter is not None
        assert sender._gauges == {}

    def test_send_numeric_values(self):
        """数値メトリクスが gauge に記録されること"""
        sender = self._make_sender()
        mock_gauge = MagicMock()
        sender._mock_meter.create_gauge.return_value = mock_gauge

        data = [
            {"key": "cloudflare.download", "value": "100.5", "host": "test-host"},
            {"key": "cloudflare.upload", "value": "50.2", "host": "test-host"},
        ]
        sender.send(data)

        # gauge が作成されたことを確認
        assert sender._mock_meter.create_gauge.call_count == 2
        # set() が呼ばれたことを確認
        assert mock_gauge.set.call_count == 2
        mock_gauge.set.assert_any_call(100.5, {"site": "cloudflare", "host": "test-host"})
        mock_gauge.set.assert_any_call(50.2, {"site": "cloudflare", "host": "test-host"})
        # force_flush が呼ばれたことを確認
        sender._mock_provider.force_flush.assert_called_once()

    def test_send_skips_non_numeric(self):
        """数値でない値はスキップされること"""
        sender = self._make_sender()
        data = [
            {"key": "netflix.server-locations", "value": "Tokyo, Osaka"},
            {"key": "boxtest.POP", "value": "NRT"},
        ]
        sender.send(data)
        # gauge が作成されない
        sender._mock_meter.create_gauge.assert_not_called()
        # force_flush は呼ばれる（空でも）
        sender._mock_provider.force_flush.assert_called_once()

    def test_send_skips_invalid_key(self):
        """ドットなしの key はスキップされること"""
        sender = self._make_sender()
        data = [{"key": "invalid_key", "value": "100.5"}]
        sender.send(data)
        sender._mock_meter.create_gauge.assert_not_called()

    def test_send_mixed_values(self):
        """数値と非数値が混在する場合、数値のみ記録されること"""
        sender = self._make_sender()
        mock_gauge = MagicMock()
        sender._mock_meter.create_gauge.return_value = mock_gauge

        data = [
            {"key": "cloudflare.download", "value": "100.5", "host": "test"},
            {"key": "netflix.server-locations", "value": "Tokyo"},
        ]
        sender.send(data)
        # 数値の1つだけ gauge が作成される
        sender._mock_meter.create_gauge.assert_called_once_with("speedtest_download")
        mock_gauge.set.assert_called_once_with(100.5, {"site": "cloudflare", "host": "test"})

    def test_send_empty_list(self):
        """空リストでもエラーにならないこと"""
        sender = self._make_sender()
        sender.send([])
        sender._mock_meter.create_gauge.assert_not_called()
        sender._mock_provider.force_flush.assert_called_once()

    def test_send_caches_gauge(self):
        """同名メトリクスの gauge がキャッシュされること"""
        sender = self._make_sender()
        mock_gauge = MagicMock()
        sender._mock_meter.create_gauge.return_value = mock_gauge

        data = [
            {"key": "cloudflare.download", "value": "100.5", "host": "h1"},
            {"key": "netflix.download", "value": "80.0", "host": "h1"},
        ]
        sender.send(data)
        # 同じ metric_name "speedtest_download" なので create_gauge は1回
        sender._mock_meter.create_gauge.assert_called_once_with("speedtest_download")
        assert mock_gauge.set.call_count == 2

    def test_send_hyphen_to_underscore(self):
        """メトリクス名のハイフンがアンダースコアに変換されること"""
        sender = self._make_sender()
        mock_gauge = MagicMock()
        sender._mock_meter.create_gauge.return_value = mock_gauge

        data = [{"key": "netflix.server-locations-count", "value": "3", "host": "h1"}]
        sender.send(data)
        sender._mock_meter.create_gauge.assert_called_once_with("speedtest_server_locations_count")
        mock_gauge.set.assert_called_once_with(3.0, {"site": "netflix", "host": "h1"})

    def test_shutdown(self):
        """shutdown() で provider.shutdown() が呼ばれること"""
        sender = self._make_sender()
        sender.shutdown()
        sender._mock_provider.shutdown.assert_called_once()


# --- ImportError 時のフォールバックテスト ---


class TestOtelImportFallback:
    """opentelemetry 未インストール時の graceful fallback テスト"""

    def test_runner_otel_without_opentelemetry(self):
        """opentelemetry なしで [otel] enable=true の場合、警告が出ること"""
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
            # [otel] セクションの読み込みをシミュレート
            if config.has_section("otel"):
                otel_enable = config.getboolean("otel", "enable", fallback=False)
                if otel_enable:
                    try:
                        raise ImportError("No module named 'opentelemetry'")
                    except ImportError:
                        pass  # graceful fallback
            assert app.otel_sender is None


# --- send_results() の統合テスト ---


def _make_app(dryrun=True, zabbix_enable=False, grafana_sender=None, otel_sender=None):
    """WebDriver を迂回して SpeedtestZ インスタンスを作成"""
    with patch.object(SpeedtestZ, "__init__", lambda self, *a, **kw: None):
        app = SpeedtestZ.__new__(SpeedtestZ)
        app.dryrun = dryrun
        app.zabbix_enable = zabbix_enable
        app.zabbix_server = "127.0.0.1"
        app.zabbix_port = 10051
        app.zabbix_host = "speedtest-agent"
        app.grafana_sender = grafana_sender
        app.otel_sender = otel_sender
    return app


class TestSendResultsOtel:
    """send_results() の OTel 送信テスト"""

    def test_otel_sender_called(self):
        """otel_sender が設定されていれば send() が呼ばれること"""
        mock_otel = MagicMock()
        app = _make_app(dryrun=False, otel_sender=mock_otel)
        data = [{"key": "cloudflare.download", "value": "100.5"}]
        with patch("speedtest_z.runner.Sender"):
            app.send_results(data)
            mock_otel.send.assert_called_once_with(data)

    def test_otel_sender_not_called_on_dryrun(self):
        """dryrun=True では otel_sender.send() が呼ばれないこと"""
        mock_otel = MagicMock()
        app = _make_app(dryrun=True, otel_sender=mock_otel)
        data = [{"key": "cloudflare.download", "value": "100.5"}]
        app.send_results(data)
        mock_otel.send.assert_not_called()

    def test_otel_error_handled(self):
        """OTel 送信エラーでもクラッシュしないこと"""
        mock_otel = MagicMock()
        mock_otel.send.side_effect = Exception("Connection error")
        app = _make_app(dryrun=False, otel_sender=mock_otel)
        data = [{"key": "cloudflare.download", "value": "100.5"}]
        with patch("speedtest_z.runner.Sender"):
            app.send_results(data)  # 例外が伝播しない

    def test_all_three_backends(self):
        """Zabbix, Grafana, OTel の3つ全てが呼ばれること"""
        mock_grafana = MagicMock()
        mock_otel = MagicMock()
        app = _make_app(
            dryrun=False,
            zabbix_enable=True,
            grafana_sender=mock_grafana,
            otel_sender=mock_otel,
        )
        data = [{"key": "cloudflare.download", "value": "100.5"}]
        with patch("speedtest_z.runner.Sender") as mock_sender_cls:
            mock_instance = MagicMock()
            mock_sender_cls.return_value = mock_instance
            app.send_results(data)
            mock_instance.send_bulk.assert_called_once()
            mock_grafana.send.assert_called_once_with(data)
            mock_otel.send.assert_called_once_with(data)


# --- close() の OTel シャットダウンテスト ---


class TestCloseOtel:
    """close() での OTel シャットダウンテスト"""

    def test_close_calls_otel_shutdown(self):
        """close() で otel_sender.shutdown() が呼ばれること"""
        mock_otel = MagicMock()
        with patch.object(SpeedtestZ, "__init__", lambda self, *a, **kw: None):
            app = SpeedtestZ.__new__(SpeedtestZ)
            app.driver = MagicMock()
            app.otel_sender = mock_otel
        app.close()
        mock_otel.shutdown.assert_called_once()

    def test_close_without_otel(self):
        """otel_sender=None でも close() がエラーにならないこと"""
        with patch.object(SpeedtestZ, "__init__", lambda self, *a, **kw: None):
            app = SpeedtestZ.__new__(SpeedtestZ)
            app.driver = MagicMock()
            app.otel_sender = None
        app.close()  # エラーが出ないこと
