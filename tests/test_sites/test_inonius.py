"""inonius サイトランナーのテスト"""

from unittest.mock import MagicMock, patch

from selenium.common.exceptions import TimeoutException

from speedtest_z.sites.inonius import _inonius_fallback_start, run_inonius


class TestInoniusFallbackStart:
    """_inonius_fallback_start() のテスト"""

    def test_fallback_returns_true_when_running(self, mock_app):
        """astro-island が存在し dialog がない場合は True"""
        with patch("speedtest_z.sites.inonius.WebDriverWait") as mock_wait:
            mock_wait.return_value.until.return_value = True
            result = _inonius_fallback_start(mock_app)
        assert result is True

    def test_fallback_returns_false_on_timeout(self, mock_app):
        """タイムアウト時は False を返しスナップショット保存"""
        mock_app.take_snapshot = MagicMock()
        with patch("speedtest_z.sites.inonius.WebDriverWait") as mock_wait:
            mock_wait.return_value.until.side_effect = TimeoutException()
            result = _inonius_fallback_start(mock_app)
        assert result is False
        mock_app.take_snapshot.assert_called_once_with("inonius_error_fallback")


class TestRunInonius:
    """run_inonius() の統合テスト"""

    def test_skip_when_should_run_false(self, mock_app):
        """_should_run が False の場合スキップ"""
        mock_app._should_run = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_inonius(mock_app)
        mock_app.send_results.assert_not_called()

    def test_skip_when_load_fails(self, mock_app):
        """ページ読み込み失敗時にスキップ"""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_inonius(mock_app)
        mock_app.send_results.assert_not_called()

    def test_auto_consent_clicks_button(self, mock_app):
        """auto_consent=True の場合、同意ボタンを自動クリック"""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        mock_btn = MagicMock()
        mock_element = MagicMock()
        mock_element.text = "100"

        with patch("speedtest_z.sites.inonius.WebDriverWait") as mock_wait:
            # 1回目: ボタンクリック待ち → ボタン返す
            # 2回目: 完了待ち → True
            mock_wait_inst = MagicMock()
            mock_wait.return_value = mock_wait_inst
            mock_wait_inst.until.side_effect = [mock_btn, True]
            mock_app.driver.find_element.return_value = mock_element

            run_inonius(mock_app)

        mock_btn.click.assert_called_once()
