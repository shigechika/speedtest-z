"""cloudflare サイトランナーのテスト"""

from unittest.mock import MagicMock, patch

from selenium.common.exceptions import NoSuchElementException

from speedtest_z.sites.cloudflare import _extract_by_label, run_cloudflare


def _make_driver_with_label(label_text, parent_text):
    """ラベル付きの DOM 要素をモックした WebDriver を返す"""
    driver = MagicMock()
    label_el = MagicMock()
    parent_el = MagicMock()
    parent_el.text = parent_text
    label_el.find_element.return_value = parent_el
    driver.find_element.return_value = label_el
    return driver


class TestExtractByLabel:
    """_extract_by_label() の抽出ロジックテスト"""

    def test_extract_download_mbps(self):
        """Download 150.3 Mbps を抽出"""
        driver = _make_driver_with_label("Download", "Download 150.3 Mbps")
        result = _extract_by_label(driver, "Download", "Mbps")
        assert result == "150.3"

    def test_extract_upload_mbps(self):
        """Upload 45.7 Mbps を抽出"""
        driver = _make_driver_with_label("Upload", "Upload 45.7 Mbps")
        result = _extract_by_label(driver, "Upload", "Mbps")
        assert result == "45.7"

    def test_extract_latency_ms(self):
        """Latency 12.5 ms を抽出"""
        driver = _make_driver_with_label("Latency", "Latency 12.5 ms")
        result = _extract_by_label(driver, "Latency", "ms")
        assert result == "12.5"

    def test_extract_jitter_microseconds(self):
        """Jitter がマイクロ秒 (μs) の場合、ミリ秒に変換"""
        driver = _make_driver_with_label("Jitter", "Jitter 500 \u03bcs")
        result = _extract_by_label(driver, "Jitter", r"ms|\u03bcs|us")
        assert result == "0.500"

    def test_extract_jitter_us_ascii(self):
        """Jitter が ASCII us の場合もミリ秒に変換"""
        driver = _make_driver_with_label("Jitter", "Jitter 200 us")
        result = _extract_by_label(driver, "Jitter", r"ms|\u03bcs|us")
        assert result == "0.200"

    def test_extract_jitter_ms(self):
        """Jitter が ms の場合はそのまま"""
        driver = _make_driver_with_label("Jitter", "Jitter 3.2 ms")
        result = _extract_by_label(driver, "Jitter", r"ms|\u03bcs|us")
        assert result == "3.2"

    def test_extract_integer_value(self):
        """整数値（小数点なし）も抽出可能"""
        driver = _make_driver_with_label("Download", "Download 200 Mbps")
        result = _extract_by_label(driver, "Download", "Mbps")
        assert result == "200.0"

    def test_extract_no_element_returns_empty(self):
        """要素が見つからない場合は空文字を返す"""
        driver = MagicMock()
        driver.find_element.side_effect = NoSuchElementException()
        result = _extract_by_label(driver, "Download", "Mbps")
        assert result == ""

    def test_extract_no_match_returns_empty(self):
        """パターンに合致しない場合は空文字を返す"""
        driver = _make_driver_with_label("Download", "Download N/A")
        result = _extract_by_label(driver, "Download", "Mbps")
        assert result == ""

    def test_extract_parent_no_digits_goes_grandparent(self):
        """parent に数字がない場合は grandparent を探索"""
        driver = MagicMock()
        label_el = MagicMock()
        parent_el = MagicMock()
        grandparent_el = MagicMock()
        parent_el.text = "Download"  # 数字なし
        grandparent_el.text = "Download 99.9 Mbps"
        parent_el.find_element.return_value = grandparent_el
        label_el.find_element.return_value = parent_el
        driver.find_element.return_value = label_el
        result = _extract_by_label(driver, "Download", "Mbps")
        assert result == "99.9"


class TestRunCloudflare:
    """run_cloudflare() の統合テスト"""

    def test_skip_when_should_run_false(self, mock_app):
        """_should_run が False の場合スキップ"""
        mock_app._should_run = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_cloudflare(mock_app)
        mock_app.send_results.assert_not_called()

    def test_skip_when_load_fails(self, mock_app):
        """ページ読み込み失敗時にスキップ"""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_cloudflare(mock_app)
        mock_app.send_results.assert_not_called()

    def test_sends_data_on_success(self, mock_app):
        """正常にデータ抽出・送信される"""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        with (
            patch("speedtest_z.sites.cloudflare.WebDriverWait"),
            patch("speedtest_z.sites.cloudflare.time"),
            patch(
                "speedtest_z.sites.cloudflare._extract_by_label",
                side_effect=["100.5", "50.2", "10.1", "1.5"],
            ),
        ):
            run_cloudflare(mock_app)

        mock_app.send_results.assert_called_once()
        data = mock_app.send_results.call_args[0][0]
        assert len(data) == 4
        assert data[0]["key"] == "cloudflare.download"
        assert data[0]["value"] == "100.5"
        assert data[1]["key"] == "cloudflare.upload"
        assert data[2]["key"] == "cloudflare.latency"
        assert data[3]["key"] == "cloudflare.jitter"
