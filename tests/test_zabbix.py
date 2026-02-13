"""Zabbix 送信ロジックのテスト"""

from unittest.mock import patch, MagicMock

from speedtest_z.main import SpeedtestZ


def _make_app(dryrun=True):
    """WebDriver を迂回して SpeedtestZ インスタンスを作成"""
    with patch.object(SpeedtestZ, "__init__", lambda self, *a, **kw: None):
        app = SpeedtestZ.__new__(SpeedtestZ)
        app.dryrun = dryrun
        app.zabbix_server = "127.0.0.1"
        app.zabbix_port = 10051
        app.zabbix_host = "speedtest-agent"
    return app


class TestSendToZabbix:
    """send_to_zabbix() のテスト"""

    def test_empty_list(self):
        """空リストでは何もしない"""
        app = _make_app()
        with patch("speedtest_z.main.Sender") as mock_sender:
            app.send_to_zabbix([])
            mock_sender.assert_not_called()

    def test_dryrun_no_send(self):
        """dryrun=True では Sender.send() が呼ばれない"""
        app = _make_app(dryrun=True)
        data = [{"key": "speedtest.dl", "value": "100.5"}]
        with patch("speedtest_z.main.Sender") as mock_sender:
            app.send_to_zabbix(data)
            mock_sender.assert_not_called()

    def test_send_called(self):
        """dryrun=False では Sender が生成され send() が呼ばれる"""
        app = _make_app(dryrun=False)
        data = [{"key": "speedtest.dl", "value": "100.5"}]
        with patch("speedtest_z.main.Sender") as mock_sender_cls:
            mock_instance = MagicMock()
            mock_sender_cls.return_value = mock_instance
            app.send_to_zabbix(data)

            mock_sender_cls.assert_called_once_with("127.0.0.1", 10051)
            mock_instance.send.assert_called_once()

    def test_sender_data_construction(self):
        """SenderData が正しく構築される"""
        app = _make_app(dryrun=False)
        data = [
            {"key": "speedtest.dl", "value": "100.5"},
            {"key": "speedtest.ul", "value": "50.2"},
        ]
        with patch("speedtest_z.main.Sender") as mock_sender_cls, \
             patch("speedtest_z.main.SenderData") as mock_sd:
            mock_instance = MagicMock()
            mock_sender_cls.return_value = mock_instance
            app.send_to_zabbix(data)

            # デフォルトホスト名で SenderData が2回呼ばれる
            assert mock_sd.call_count == 2
            mock_sd.assert_any_call("speedtest-agent", "speedtest.dl", "100.5")
            mock_sd.assert_any_call("speedtest-agent", "speedtest.ul", "50.2")

    def test_custom_host(self):
        """データに host を含む場合はそちらを使う"""
        app = _make_app(dryrun=False)
        data = [{"host": "custom-host", "key": "speedtest.dl", "value": "99"}]
        with patch("speedtest_z.main.Sender") as mock_sender_cls, \
             patch("speedtest_z.main.SenderData") as mock_sd:
            mock_sender_cls.return_value = MagicMock()
            app.send_to_zabbix(data)

            mock_sd.assert_called_once_with("custom-host", "speedtest.dl", "99")

    def test_send_error_handled(self):
        """送信エラーでもクラッシュしない"""
        app = _make_app(dryrun=False)
        data = [{"key": "speedtest.dl", "value": "100"}]
        with patch("speedtest_z.main.Sender") as mock_sender_cls:
            mock_instance = MagicMock()
            mock_instance.send.side_effect = Exception("Connection refused")
            mock_sender_cls.return_value = mock_instance

            # 例外が伝播しないことを確認
            app.send_to_zabbix(data)
