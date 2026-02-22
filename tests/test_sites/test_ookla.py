"""ookla サイトランナーのテスト"""

from unittest.mock import MagicMock

from speedtest_z.sites.ookla import run_ookla


class TestRunOokla:
    """run_ookla() のテスト"""

    def test_skip_when_should_run_false(self, mock_app):
        """_should_run が False の場合スキップ"""
        mock_app._should_run = MagicMock(return_value=False)
        mock_app.send_to_zabbix = MagicMock()
        run_ookla(mock_app)
        mock_app.send_to_zabbix.assert_not_called()

    def test_skip_when_load_fails(self, mock_app):
        """ページ読み込み失敗時にスキップ"""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=False)
        mock_app.send_to_zabbix = MagicMock()
        run_ookla(mock_app)
        mock_app.send_to_zabbix.assert_not_called()
