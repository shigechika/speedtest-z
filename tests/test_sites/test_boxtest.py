"""Tests for the box-test.com site runner."""

from unittest.mock import MagicMock, PropertyMock, patch

from selenium.common.exceptions import NoSuchElementException, TimeoutException

from speedtest_z.sites.boxtest import run_boxtest, wait_for_stability


class TestWaitForStability:
    """Tests for wait_for_stability()."""

    def test_stability_reached_on_second_same_value(self, mock_app):
        """Stability detected when two consecutive readings match."""
        element = MagicMock()
        # 1st: "10ms", 2nd: "12ms", 3rd: "12ms" -> stable
        type(element).text = PropertyMock(side_effect=["10ms", "12ms", "12ms"])
        mock_app.driver.find_element.return_value = element

        with patch("speedtest_z.sites.boxtest.time"):
            wait_for_stability(mock_app)

        assert mock_app.driver.find_element.call_count == 3

    def test_stability_immediate_match(self, mock_app):
        """Exit immediately when first two readings match."""
        element = MagicMock()
        type(element).text = PropertyMock(side_effect=["5ms", "5ms"])
        mock_app.driver.find_element.return_value = element

        with patch("speedtest_z.sites.boxtest.time"):
            wait_for_stability(mock_app)

        assert mock_app.driver.find_element.call_count == 2

    def test_stability_timeout(self, mock_app):
        """Loop 12 times without stability."""
        element = MagicMock()
        type(element).text = PropertyMock(side_effect=[f"{i}ms" for i in range(12)])
        mock_app.driver.find_element.return_value = element

        with patch("speedtest_z.sites.boxtest.time"):
            wait_for_stability(mock_app)

        assert mock_app.driver.find_element.call_count == 12

    def test_stability_element_not_found(self, mock_app):
        """Retry until timeout when element is not found."""
        mock_app.driver.find_element.side_effect = NoSuchElementException()

        with patch("speedtest_z.sites.boxtest.time"):
            wait_for_stability(mock_app)

        assert mock_app.driver.find_element.call_count == 12

    def test_stability_empty_text_not_counted(self, mock_app):
        """Empty text is not used for matching."""
        element = MagicMock()
        # empty -> "10ms" -> "10ms" = stable
        type(element).text = PropertyMock(side_effect=["", "10ms", "10ms"])
        mock_app.driver.find_element.return_value = element

        with patch("speedtest_z.sites.boxtest.time"):
            wait_for_stability(mock_app)

        assert mock_app.driver.find_element.call_count == 3


class TestRunBoxtest:
    """Tests for run_boxtest()."""

    def test_skip_when_should_run_false(self, mock_app):
        """Skip when _should_run returns False."""
        mock_app._should_run = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_boxtest(mock_app)
        mock_app.send_results.assert_not_called()

    def test_skip_when_load_fails(self, mock_app):
        """Skip when page load fails."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_boxtest(mock_app)
        mock_app.send_results.assert_not_called()

    def test_sends_results_on_success(self, mock_app):
        """Send results with parsed numeric values on success."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.BOXTEST_TIMEOUT = 90

        # Mock toggle button already at target size
        toggle_btn = MagicMock()
        toggle_btn.text = "100 MB"

        # Mock Go! button
        go_btn = MagicMock()

        # Build result elements for find_element calls
        base_xp = "//div[@id='pop-test-manager']//table/tbody/tr"
        latency_xp = (
            "//div[contains(text(), 'Average latency to Box')]"
            "/ancestor::div[contains(@class, 'card')]"
            "//*[local-name()='tspan' and contains(., 'Avg:')]"
        )
        results = {
            f"{base_xp}/td[1]/b": "TYO",  # POP (string)
            f"{base_xp}/td[2]": "250.5 Mbps",  # DownloadSpeed
            f"{base_xp}/td[3]": "5.2 sec",  # DownloadDuration
            f"{base_xp}/td[4]": "10 ms",  # DownloadRTT
            f"{base_xp}/td[5]": "180.3 Mbps",  # UploadSpeed
            f"{base_xp}/td[6]": "6.1 sec",  # UploadDuration
            f"{base_xp}/td[7]": "12 ms",  # UploadRTT
            latency_xp: "Avg: 8 ms",  # latency
        }

        def _find(by, xpath):
            if xpath == "//button[contains(text(), 'Go!')]":
                return go_btn
            if xpath in results:
                el = MagicMock()
                el.text = results[xpath]
                return el
            raise NoSuchElementException(f"not found: {xpath}")

        mock_app.driver.find_element.side_effect = _find

        with (
            patch("speedtest_z.sites.boxtest.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.boxtest.time"),
            patch("speedtest_z.sites.boxtest.wait_for_stability"),
        ):
            mock_app.wait.until.return_value = toggle_btn
            mock_wdw.return_value.until.return_value = True
            run_boxtest(mock_app)

        mock_app.send_results.assert_called_once()
        data = mock_app.send_results.call_args[0][0]

        # Check POP (string item)
        pop_items = [d for d in data if d["key"] == "boxtest.POP"]
        assert len(pop_items) == 1
        assert pop_items[0]["value"] == "TYO"

        # Check numeric items are parsed correctly
        dl_items = [d for d in data if d["key"] == "boxtest.DownloadSpeed"]
        assert len(dl_items) == 1
        assert dl_items[0]["value"] == "250.5"

        lat_items = [d for d in data if d["key"] == "boxtest.latency"]
        assert len(lat_items) == 1
        assert lat_items[0]["value"] == "8"  # "Avg: 8 ms" -> "8"

    def test_go_button_not_found(self, mock_app):
        """Return early when Go! button is not found."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.BOXTEST_TIMEOUT = 90

        toggle_btn = MagicMock()
        toggle_btn.text = "100 MB"
        mock_app.driver.find_element.side_effect = NoSuchElementException("no Go!")

        with (
            patch("speedtest_z.sites.boxtest.WebDriverWait"),
            patch("speedtest_z.sites.boxtest.time"),
            patch("speedtest_z.sites.boxtest.wait_for_stability"),
        ):
            mock_app.wait.until.return_value = toggle_btn
            run_boxtest(mock_app)

        mock_app.send_results.assert_not_called()
        mock_app.take_snapshot.assert_any_call("boxtest_error_start")

    def test_timeout_waiting_for_results(self, mock_app):
        """Return early on timeout waiting for upload speed value."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.BOXTEST_TIMEOUT = 90

        toggle_btn = MagicMock()
        toggle_btn.text = "100 MB"
        go_btn = MagicMock()

        def _find(by, xpath):
            if xpath == "//button[contains(text(), 'Go!')]":
                return go_btn
            raise NoSuchElementException()

        mock_app.driver.find_element.side_effect = _find

        with (
            patch("speedtest_z.sites.boxtest.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.boxtest.time"),
            patch("speedtest_z.sites.boxtest.wait_for_stability"),
        ):
            mock_app.wait.until.return_value = toggle_btn
            mock_wdw.return_value.until.side_effect = TimeoutException()
            run_boxtest(mock_app)

        mock_app.send_results.assert_not_called()
        mock_app.take_snapshot.assert_any_call("boxtest_timeout")

    def test_numeric_value_parsing(self, mock_app):
        """Numeric values are cleaned: 'Avg:' prefix and 'ms' unit removed."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.BOXTEST_TIMEOUT = 90

        toggle_btn = MagicMock()
        toggle_btn.text = "100 MB"
        go_btn = MagicMock()

        base_xp = "//div[@id='pop-test-manager']//table/tbody/tr"
        latency_xp = (
            "//div[contains(text(), 'Average latency to Box')]"
            "/ancestor::div[contains(@class, 'card')]"
            "//*[local-name()='tspan' and contains(., 'Avg:')]"
        )
        results = {
            f"{base_xp}/td[1]/b": "SFO",
            f"{base_xp}/td[2]": "100 Mbps",
            f"{base_xp}/td[3]": "10 sec",
            f"{base_xp}/td[4]": "15 ms",
            f"{base_xp}/td[5]": "50 Mbps",
            f"{base_xp}/td[6]": "20 sec",
            f"{base_xp}/td[7]": "18 ms",
            latency_xp: "Avg: 15ms",
        }

        def _find(by, xpath):
            if xpath == "//button[contains(text(), 'Go!')]":
                return go_btn
            if xpath in results:
                el = MagicMock()
                el.text = results[xpath]
                return el
            raise NoSuchElementException()

        mock_app.driver.find_element.side_effect = _find

        with (
            patch("speedtest_z.sites.boxtest.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.boxtest.time"),
            patch("speedtest_z.sites.boxtest.wait_for_stability"),
        ):
            mock_app.wait.until.return_value = toggle_btn
            mock_wdw.return_value.until.return_value = True
            run_boxtest(mock_app)

        data = mock_app.send_results.call_args[0][0]
        lat_items = [d for d in data if d["key"] == "boxtest.latency"]
        assert lat_items[0]["value"] == "15"  # "Avg: 15ms" -> remove Avg:, ms -> "15"

    def test_missing_elements_skipped_gracefully(self, mock_app):
        """Missing elements are logged as warnings and skipped."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.BOXTEST_TIMEOUT = 90

        toggle_btn = MagicMock()
        toggle_btn.text = "100 MB"
        go_btn = MagicMock()

        # Only provide Go! button and POP, everything else raises
        base_xp = "//div[@id='pop-test-manager']//table/tbody/tr"
        pop_el = MagicMock()
        pop_el.text = "TYO"

        def _find(by, xpath):
            if xpath == "//button[contains(text(), 'Go!')]":
                return go_btn
            if xpath == f"{base_xp}/td[1]/b":
                return pop_el
            raise NoSuchElementException(f"not found: {xpath}")

        mock_app.driver.find_element.side_effect = _find

        with (
            patch("speedtest_z.sites.boxtest.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.boxtest.time"),
            patch("speedtest_z.sites.boxtest.wait_for_stability"),
        ):
            mock_app.wait.until.return_value = toggle_btn
            mock_wdw.return_value.until.return_value = True
            run_boxtest(mock_app)

        # Should still send results with just POP
        mock_app.send_results.assert_called_once()
        data = mock_app.send_results.call_args[0][0]
        assert len(data) == 1
        assert data[0]["key"] == "boxtest.POP"

    def test_snapshot_always_taken(self, mock_app):
        """Snapshot is always taken in the finally block."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.BOXTEST_TIMEOUT = 90

        toggle_btn = MagicMock()
        toggle_btn.text = "100 MB"
        mock_app.driver.find_element.side_effect = NoSuchElementException()

        with (
            patch("speedtest_z.sites.boxtest.WebDriverWait"),
            patch("speedtest_z.sites.boxtest.time"),
            patch("speedtest_z.sites.boxtest.wait_for_stability"),
        ):
            mock_app.wait.until.return_value = toggle_btn
            run_boxtest(mock_app)

        mock_app.take_snapshot.assert_any_call("boxtest")

    def test_size_toggle_clicks(self, mock_app):
        """Toggle button is clicked until target size is reached."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.BOXTEST_TIMEOUT = 90

        # Toggle cycles: "10 MB" -> "50 MB" -> "100 MB"
        toggle_btn = MagicMock()
        type(toggle_btn).text = PropertyMock(side_effect=["10 MB", "50 MB", "100 MB"])
        mock_app.driver.find_element.side_effect = NoSuchElementException()

        with (
            patch("speedtest_z.sites.boxtest.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.boxtest.time"),
            patch("speedtest_z.sites.boxtest.wait_for_stability"),
        ):
            mock_app.wait.until.return_value = toggle_btn
            mock_wdw.return_value.until.side_effect = TimeoutException()
            run_boxtest(mock_app)

        # Should click twice (10MB->50MB, 50MB->100MB), stop at 100MB
        assert toggle_btn.click.call_count == 2
