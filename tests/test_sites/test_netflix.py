"""Tests for the Netflix fast.com site runner."""

from unittest.mock import MagicMock, patch

from selenium.common.exceptions import NoSuchElementException, TimeoutException

from speedtest_z.sites.netflix import run_netflix


def _mock_find_element_results(
    download="150", upload="45", latency="12", server_locations="Tokyo"
):
    """Return a side_effect function for find_element returning result texts."""
    results = {
        "speed-value": download,
        "upload-value": upload,
        "latency-value": latency,
        "server-locations": server_locations,
    }

    def _find(by, elem_id):
        if elem_id in results:
            el = MagicMock()
            el.text = results[elem_id]
            return el
        raise NoSuchElementException(f"Element {elem_id} not found")

    return _find


class TestRunNetflix:
    """Tests for run_netflix()."""

    def test_skip_when_should_run_false(self, mock_app):
        """Skip when _should_run returns False."""
        mock_app._should_run = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_netflix(mock_app)
        mock_app.send_results.assert_not_called()

    def test_skip_when_load_fails(self, mock_app):
        """Skip when page load fails."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_netflix(mock_app)
        mock_app.send_results.assert_not_called()

    def test_sends_results_on_success(self, mock_app):
        """Send download/upload/latency/server-locations on success."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.driver.find_element.side_effect = _mock_find_element_results(
            "320", "95", "8", "Osaka"
        )

        mock_more_btn = MagicMock()
        with (
            patch("speedtest_z.sites.netflix.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.netflix.time"),
        ):
            mock_app.wait.until.return_value = mock_more_btn
            mock_wdw.return_value.until.return_value = True
            run_netflix(mock_app)

        mock_app.send_results.assert_called_once()
        data = mock_app.send_results.call_args[0][0]
        assert len(data) == 4
        assert data[0]["key"] == "netflix.download"
        assert data[0]["value"] == "320"
        assert data[1]["key"] == "netflix.upload"
        assert data[1]["value"] == "95"
        assert data[2]["key"] == "netflix.latency"
        assert data[2]["value"] == "8"
        assert data[3]["key"] == "netflix.server-locations"
        assert data[3]["value"] == "Osaka"

    def test_more_details_click_failure(self, mock_app):
        """Return early when 'More Info' button click fails."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        mock_app.wait.until.side_effect = Exception("element not found")
        run_netflix(mock_app)

        mock_app.send_results.assert_not_called()
        mock_app.take_snapshot.assert_any_call("netflix_error_click")

    def test_timeout_waiting_for_results(self, mock_app):
        """Return early on timeout waiting for 'succeeded' indicator."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        with (
            patch("speedtest_z.sites.netflix.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.netflix.time"),
        ):
            mock_app.wait.until.return_value = MagicMock()  # more button
            mock_wdw.return_value.until.side_effect = TimeoutException()
            run_netflix(mock_app)

        mock_app.send_results.assert_not_called()
        mock_app.take_snapshot.assert_any_call("netflix_timeout")

    def test_result_elements_not_found(self, mock_app):
        """Return early when result elements are not in DOM."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.driver.find_element.side_effect = NoSuchElementException("not found")

        with (
            patch("speedtest_z.sites.netflix.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.netflix.time"),
        ):
            mock_app.wait.until.return_value = MagicMock()
            mock_wdw.return_value.until.return_value = True
            run_netflix(mock_app)

        mock_app.send_results.assert_not_called()

    def test_snapshot_always_taken(self, mock_app):
        """Snapshot is always taken in the finally block."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.driver.find_element.side_effect = _mock_find_element_results()

        with (
            patch("speedtest_z.sites.netflix.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.netflix.time"),
        ):
            mock_app.wait.until.return_value = MagicMock()
            mock_wdw.return_value.until.return_value = True
            run_netflix(mock_app)

        mock_app.take_snapshot.assert_any_call("netflix")

    def test_more_button_clicked_via_js(self, mock_app):
        """More details button is clicked via JavaScript."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.driver.find_element.side_effect = _mock_find_element_results()

        more_btn = MagicMock()
        with (
            patch("speedtest_z.sites.netflix.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.netflix.time"),
        ):
            mock_app.wait.until.return_value = more_btn
            mock_wdw.return_value.until.return_value = True
            run_netflix(mock_app)

        mock_app.driver.execute_script.assert_called_once_with("arguments[0].click();", more_btn)

    def test_zabbix_host_in_data(self, mock_app):
        """Each data item includes the correct zabbix_host."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.zabbix_host = "custom-host"
        mock_app.driver.find_element.side_effect = _mock_find_element_results()

        with (
            patch("speedtest_z.sites.netflix.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.netflix.time"),
        ):
            mock_app.wait.until.return_value = MagicMock()
            mock_wdw.return_value.until.return_value = True
            run_netflix(mock_app)

        data = mock_app.send_results.call_args[0][0]
        for item in data:
            assert item["host"] == "custom-host"
