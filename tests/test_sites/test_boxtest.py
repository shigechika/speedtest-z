"""boxtest サイトランナーのテスト"""

from unittest.mock import MagicMock, PropertyMock, patch

from selenium.common.exceptions import NoSuchElementException

from speedtest_z.sites.boxtest import run_boxtest, wait_for_stability


class TestWaitForStability:
    """wait_for_stability() の安定性チェックテスト"""

    def test_stability_reached_on_second_same_value(self, mock_app):
        """2回連続で同じ値が返ると安定と判定"""
        element = MagicMock()
        # 1回目: "10ms", 2回目: "12ms", 3回目: "12ms" で安定
        element.text = PropertyMock(side_effect=["10ms", "12ms", "12ms"])
        type(element).text = PropertyMock(side_effect=["10ms", "12ms", "12ms"])
        mock_app.driver.find_element.return_value = element

        with patch("speedtest_z.sites.boxtest.time"):
            wait_for_stability(mock_app)

        assert mock_app.driver.find_element.call_count == 3

    def test_stability_immediate_match(self, mock_app):
        """最初の2回で一致すれば即座に終了"""
        element = MagicMock()
        type(element).text = PropertyMock(side_effect=["5ms", "5ms"])
        mock_app.driver.find_element.return_value = element

        with patch("speedtest_z.sites.boxtest.time"):
            wait_for_stability(mock_app)

        assert mock_app.driver.find_element.call_count == 2

    def test_stability_timeout(self, mock_app):
        """12回ループしても安定しない場合はタイムアウト"""
        element = MagicMock()
        # 全て異なる値
        type(element).text = PropertyMock(side_effect=[f"{i}ms" for i in range(12)])
        mock_app.driver.find_element.return_value = element

        with patch("speedtest_z.sites.boxtest.time"):
            wait_for_stability(mock_app)

        assert mock_app.driver.find_element.call_count == 12

    def test_stability_element_not_found(self, mock_app):
        """要素が見つからない場合もタイムアウトまでリトライ"""
        mock_app.driver.find_element.side_effect = NoSuchElementException()

        with patch("speedtest_z.sites.boxtest.time"):
            wait_for_stability(mock_app)

        assert mock_app.driver.find_element.call_count == 12

    def test_stability_empty_text_not_counted(self, mock_app):
        """空文字は一致判定に使わない（次のループで再取得）"""
        element = MagicMock()
        # 空文字 → "10ms" → "10ms" で安定
        type(element).text = PropertyMock(side_effect=["", "10ms", "10ms"])
        mock_app.driver.find_element.return_value = element

        with patch("speedtest_z.sites.boxtest.time"):
            wait_for_stability(mock_app)

        assert mock_app.driver.find_element.call_count == 3


class TestRunBoxtest:
    """run_boxtest() の統合テスト"""

    def test_skip_when_should_run_false(self, mock_app):
        """_should_run が False の場合スキップ"""
        mock_app._should_run = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_boxtest(mock_app)
        mock_app.send_results.assert_not_called()

    def test_skip_when_load_fails(self, mock_app):
        """ページ読み込み失敗時にスキップ"""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_boxtest(mock_app)
        mock_app.send_results.assert_not_called()
