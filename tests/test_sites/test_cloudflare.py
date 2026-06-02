"""Tests for the cloudflare site runner."""

from unittest.mock import MagicMock, patch

from selenium.common.exceptions import NoSuchElementException, TimeoutException

from speedtest_z.sites.cloudflare import _extract_by_label, run_cloudflare


def _make_driver_with_label(label_text, parent_text):
    """Return a WebDriver mock with a labeled DOM element."""
    driver = MagicMock()
    label_el = MagicMock()
    parent_el = MagicMock()
    parent_el.text = parent_text
    label_el.find_element.return_value = parent_el
    driver.find_element.return_value = label_el
    return driver


class TestExtractByLabel:
    """Tests for the extraction logic of _extract_by_label()."""

    def test_extract_download_mbps(self):
        """Extract Download 150.3 Mbps."""
        driver = _make_driver_with_label("Download", "Download 150.3 Mbps")
        result = _extract_by_label(driver, "Download", "Mbps")
        assert result == "150.3"

    def test_extract_upload_mbps(self):
        """Extract Upload 45.7 Mbps."""
        driver = _make_driver_with_label("Upload", "Upload 45.7 Mbps")
        result = _extract_by_label(driver, "Upload", "Mbps")
        assert result == "45.7"

    def test_extract_latency_ms(self):
        """Extract Latency 12.5 ms."""
        driver = _make_driver_with_label("Latency", "Latency 12.5 ms")
        result = _extract_by_label(driver, "Latency", "ms")
        assert result == "12.5"

    def test_extract_jitter_microseconds(self):
        """Convert Jitter in microseconds (us) to milliseconds."""
        driver = _make_driver_with_label("Jitter", "Jitter 500 \u03bcs")
        result = _extract_by_label(driver, "Jitter", r"ms|\u03bcs|us")
        assert result == "0.500"

    def test_extract_jitter_us_ascii(self):
        """Convert Jitter to milliseconds when the unit is ASCII us."""
        driver = _make_driver_with_label("Jitter", "Jitter 200 us")
        result = _extract_by_label(driver, "Jitter", r"ms|\u03bcs|us")
        assert result == "0.200"

    def test_extract_jitter_ms(self):
        """Keep Jitter as-is when the unit is ms."""
        driver = _make_driver_with_label("Jitter", "Jitter 3.2 ms")
        result = _extract_by_label(driver, "Jitter", r"ms|\u03bcs|us")
        assert result == "3.2"

    def test_extract_integer_value(self):
        """Integer values (no decimal point) can also be extracted."""
        driver = _make_driver_with_label("Download", "Download 200 Mbps")
        result = _extract_by_label(driver, "Download", "Mbps")
        assert result == "200.0"

    def test_extract_no_element_returns_empty(self):
        """Return an empty string when the element is not found."""
        driver = MagicMock()
        driver.find_element.side_effect = NoSuchElementException()
        result = _extract_by_label(driver, "Download", "Mbps")
        assert result == ""

    def test_extract_no_match_returns_empty(self):
        """Return an empty string when the pattern does not match."""
        driver = _make_driver_with_label("Download", "Download N/A")
        result = _extract_by_label(driver, "Download", "Mbps")
        assert result == ""

    def test_extract_parent_no_digits_goes_grandparent(self):
        """Search the grandparent when the parent has no digits."""
        driver = MagicMock()
        label_el = MagicMock()
        parent_el = MagicMock()
        grandparent_el = MagicMock()
        parent_el.text = "Download"  # no digits
        grandparent_el.text = "Download 99.9 Mbps"
        parent_el.find_element.return_value = grandparent_el
        label_el.find_element.return_value = parent_el
        driver.find_element.return_value = label_el
        result = _extract_by_label(driver, "Download", "Mbps")
        assert result == "99.9"


class TestRunCloudflare:
    """Integration tests for run_cloudflare()."""

    def test_skip_when_should_run_false(self, mock_app):
        """Skip when _should_run returns False."""
        mock_app._should_run = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_cloudflare(mock_app)
        mock_app.send_results.assert_not_called()

    def test_skip_when_load_fails(self, mock_app):
        """Skip when the page fails to load."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_cloudflare(mock_app)
        mock_app.send_results.assert_not_called()

    def test_sends_data_on_success(self, mock_app):
        """Data is extracted and sent successfully."""
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

    def test_download_extraction_failure_returns_early(self, mock_app):
        """Return early when download speed extraction fails."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        with (
            patch("speedtest_z.sites.cloudflare.WebDriverWait"),
            patch("speedtest_z.sites.cloudflare.time"),
            patch(
                "speedtest_z.sites.cloudflare._extract_by_label",
                side_effect=["", "50.2", "10.1", "1.5"],
            ),
        ):
            run_cloudflare(mock_app)

        mock_app.send_results.assert_not_called()
        mock_app.take_snapshot.assert_any_call("cloudflare_error_parse")

    def test_timeout_waiting_for_completion(self, mock_app):
        """Continue even when Quality Scores timeout occurs."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        with (
            patch("speedtest_z.sites.cloudflare.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.cloudflare.time"),
            patch(
                "speedtest_z.sites.cloudflare._extract_by_label",
                side_effect=["100.0", "50.0", "10.0", "1.0"],
            ),
        ):
            mock_wdw.return_value.until.side_effect = [
                MagicMock(),  # Start button
                True,  # invisibility
                TimeoutException(),  # Quality Scores timeout
            ]
            run_cloudflare(mock_app)

        # Should still try to extract results after timeout
        mock_app.send_results.assert_called_once()
        mock_app.take_snapshot.assert_any_call("cloudflare_timeout")

    def test_snapshot_always_taken(self, mock_app):
        """Snapshot is always taken in the finally block."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        with (
            patch("speedtest_z.sites.cloudflare.WebDriverWait"),
            patch("speedtest_z.sites.cloudflare.time"),
            patch(
                "speedtest_z.sites.cloudflare._extract_by_label",
                side_effect=["100.0", "50.0", "10.0", "1.0"],
            ),
        ):
            run_cloudflare(mock_app)

        mock_app.take_snapshot.assert_any_call("cloudflare")

    def test_zabbix_host_in_data(self, mock_app):
        """Each data item includes the correct zabbix_host."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.zabbix_host = "cf-host"

        with (
            patch("speedtest_z.sites.cloudflare.WebDriverWait"),
            patch("speedtest_z.sites.cloudflare.time"),
            patch(
                "speedtest_z.sites.cloudflare._extract_by_label",
                side_effect=["100.0", "50.0", "10.0", "1.0"],
            ),
        ):
            run_cloudflare(mock_app)

        data = mock_app.send_results.call_args[0][0]
        for item in data:
            assert item["host"] == "cf-host"

    def test_extraction_error_returns_early(self, mock_app):
        """Return early when _extract_by_label raises an exception."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        with (
            patch("speedtest_z.sites.cloudflare.WebDriverWait"),
            patch("speedtest_z.sites.cloudflare.time"),
            patch(
                "speedtest_z.sites.cloudflare._extract_by_label",
                side_effect=Exception("extraction error"),
            ),
        ):
            run_cloudflare(mock_app)

        mock_app.send_results.assert_not_called()
