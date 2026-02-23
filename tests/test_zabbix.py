"""Zabbix 送信ロジックのテスト"""

from unittest.mock import MagicMock, patch

from speedtest_z.runner import SpeedtestZ


def _make_app(dryrun=True, zabbix_enable=True):
    """WebDriver を迂回して SpeedtestZ インスタンスを作成"""
    with patch.object(SpeedtestZ, "__init__", lambda self, *a, **kw: None):
        app = SpeedtestZ.__new__(SpeedtestZ)
        app.dryrun = dryrun
        app.zabbix_enable = zabbix_enable
        app.zabbix_server = "127.0.0.1"
        app.zabbix_port = 10051
        app.zabbix_host = "speedtest-agent"
        app.grafana_sender = None
        app.otel_sender = None
    return app


class TestSendResults:
    """send_results() のテスト"""

    def test_empty_list(self):
        """空リストでは何もしない"""
        app = _make_app()
        with patch("speedtest_z.runner.Sender") as mock_sender:
            app.send_results([])
            mock_sender.assert_not_called()

    def test_dryrun_no_send(self):
        """dryrun=True では Sender.send_bulk() が呼ばれない"""
        app = _make_app(dryrun=True)
        data = [{"key": "speedtest.dl", "value": "100.5"}]
        with patch("speedtest_z.runner.Sender") as mock_sender:
            app.send_results(data)
            mock_sender.assert_not_called()

    def test_send_called(self):
        """dryrun=False では Sender が生成され send_bulk() が呼ばれる"""
        app = _make_app(dryrun=False, zabbix_enable=True)
        data = [{"key": "speedtest.dl", "value": "100.5"}]
        with patch("speedtest_z.runner.Sender") as mock_sender_cls:
            mock_instance = MagicMock()
            mock_sender_cls.return_value = mock_instance
            app.send_results(data)

            mock_sender_cls.assert_called_once_with("127.0.0.1", 10051)
            mock_instance.send_bulk.assert_called_once()

    def test_sender_data_construction(self):
        """SenderData が正しく構築される"""
        app = _make_app(dryrun=False, zabbix_enable=True)
        data = [
            {"key": "speedtest.dl", "value": "100.5"},
            {"key": "speedtest.ul", "value": "50.2"},
        ]
        with (
            patch("speedtest_z.runner.Sender") as mock_sender_cls,
            patch("speedtest_z.runner.SenderData") as mock_sd,
        ):
            mock_instance = MagicMock()
            mock_sender_cls.return_value = mock_instance
            app.send_results(data)

            # デフォルトホスト名で SenderData が2回呼ばれる
            assert mock_sd.call_count == 2
            mock_sd.assert_any_call("speedtest-agent", "speedtest.dl", "100.5")
            mock_sd.assert_any_call("speedtest-agent", "speedtest.ul", "50.2")

    def test_custom_host(self):
        """データに host を含む場合はそちらを使う"""
        app = _make_app(dryrun=False, zabbix_enable=True)
        data = [{"host": "custom-host", "key": "speedtest.dl", "value": "99"}]
        with (
            patch("speedtest_z.runner.Sender") as mock_sender_cls,
            patch("speedtest_z.runner.SenderData") as mock_sd,
        ):
            mock_sender_cls.return_value = MagicMock()
            app.send_results(data)

            mock_sd.assert_called_once_with("custom-host", "speedtest.dl", "99")

    def test_send_error_handled(self):
        """送信エラーでもクラッシュしない"""
        app = _make_app(dryrun=False, zabbix_enable=True)
        data = [{"key": "speedtest.dl", "value": "100"}]
        with patch("speedtest_z.runner.Sender") as mock_sender_cls:
            mock_instance = MagicMock()
            mock_instance.send_bulk.side_effect = Exception("Connection refused")
            mock_sender_cls.return_value = mock_instance

            # 例外が伝播しないことを確認
            app.send_results(data)
