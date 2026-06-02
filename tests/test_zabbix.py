"""Tests for the Zabbix send logic."""

from unittest.mock import MagicMock, patch

from speedtest_z.runner import SpeedtestZ
from speedtest_z.sender import SenderManager


def _make_app(dryrun=True, zabbix_enable=True):
    """Create a SpeedtestZ instance, bypassing the WebDriver."""
    with patch.object(SpeedtestZ, "__init__", lambda self, *a, **kw: None):
        app = SpeedtestZ.__new__(SpeedtestZ)
        sender = MagicMock(spec=SenderManager)
        sender.dry_run = dryrun
        sender.zabbix_enable = zabbix_enable
        sender.zabbix_server = "127.0.0.1"
        sender.zabbix_port = 10051
        sender.zabbix_host = "speedtest-agent"
        sender.grafana_sender = None
        sender.otel_sender = None
        app.sender = sender
        app.dryrun = dryrun
        app.zabbix_enable = zabbix_enable
        app.zabbix_server = "127.0.0.1"
        app.zabbix_port = 10051
        app.zabbix_host = "speedtest-agent"
        app.grafana_sender = None
        app.otel_sender = None
    return app


def _make_sender(dryrun=True, zabbix_enable=True):
    """Create a SenderManager instance directly."""
    with patch.object(SenderManager, "__init__", lambda self, *a, **kw: None):
        sender = SenderManager.__new__(SenderManager)
        sender.dry_run = dryrun
        sender.zabbix_enable = zabbix_enable
        sender.zabbix_server = "127.0.0.1"
        sender.zabbix_port = 10051
        sender.zabbix_host = "speedtest-agent"
        sender.grafana_sender = None
        sender.otel_sender = None
    return sender


class TestSendResults:
    """Tests for send_results() (directly testing SenderManager.send())."""

    def test_empty_list(self):
        """Does nothing for an empty list."""
        sender = _make_sender()
        with patch("speedtest_z.sender.Sender") as mock_sender:
            sender.send([])
            mock_sender.assert_not_called()

    def test_dryrun_no_send(self):
        """Sender.send_bulk() is not called when dryrun=True."""
        sender = _make_sender(dryrun=True)
        data = [{"key": "speedtest.dl", "value": "100.5"}]
        with patch("speedtest_z.sender.Sender") as mock_sender:
            sender.send(data)
            mock_sender.assert_not_called()

    def test_send_called(self):
        """When dryrun=False, a Sender is created and send_bulk() is called."""
        sender = _make_sender(dryrun=False, zabbix_enable=True)
        data = [{"key": "speedtest.dl", "value": "100.5"}]
        with patch("speedtest_z.sender.Sender") as mock_sender_cls:
            mock_instance = MagicMock()
            mock_sender_cls.return_value = mock_instance
            sender.send(data)

            mock_sender_cls.assert_called_once_with("127.0.0.1", 10051)
            mock_instance.send_bulk.assert_called_once()

    def test_sender_data_construction(self):
        """SenderData is constructed correctly."""
        sender = _make_sender(dryrun=False, zabbix_enable=True)
        data = [
            {"key": "speedtest.dl", "value": "100.5"},
            {"key": "speedtest.ul", "value": "50.2"},
        ]
        with (
            patch("speedtest_z.sender.Sender") as mock_sender_cls,
            patch("speedtest_z.sender.SenderData") as mock_sd,
        ):
            mock_instance = MagicMock()
            mock_sender_cls.return_value = mock_instance
            sender.send(data)

            # SenderData is called twice with the default host name
            assert mock_sd.call_count == 2
            mock_sd.assert_any_call("speedtest-agent", "speedtest.dl", "100.5")
            mock_sd.assert_any_call("speedtest-agent", "speedtest.ul", "50.2")

    def test_custom_host(self):
        """When the data includes a host, that one is used."""
        sender = _make_sender(dryrun=False, zabbix_enable=True)
        data = [{"host": "custom-host", "key": "speedtest.dl", "value": "99"}]
        with (
            patch("speedtest_z.sender.Sender") as mock_sender_cls,
            patch("speedtest_z.sender.SenderData") as mock_sd,
        ):
            mock_sender_cls.return_value = MagicMock()
            sender.send(data)

            mock_sd.assert_called_once_with("custom-host", "speedtest.dl", "99")

    def test_send_error_handled(self):
        """A send error does not crash the run."""
        sender = _make_sender(dryrun=False, zabbix_enable=True)
        data = [{"key": "speedtest.dl", "value": "100"}]
        with patch("speedtest_z.sender.Sender") as mock_sender_cls:
            mock_instance = MagicMock()
            mock_instance.send_bulk.side_effect = Exception("Connection refused")
            mock_sender_cls.return_value = mock_instance

            # Verify the exception does not propagate
            sender.send(data)

    def test_delegation_from_app(self):
        """SpeedtestZ.send_results() delegates to SenderManager.send()."""
        app = _make_app(dryrun=False, zabbix_enable=True)
        data = [{"key": "speedtest.dl", "value": "100.5"}]
        app.send_results(data)
        app.sender.send.assert_called_once_with(data)
