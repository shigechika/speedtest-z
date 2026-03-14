"""Tests for the Google Fiber site runner."""

from unittest.mock import MagicMock, patch

from selenium.common.exceptions import TimeoutException

from speedtest_z.sites.google import run_google


def _mock_find_element_results(download="150.5", upload="45.2", ping="5"):
    """Return a side_effect function for find_element that returns result values."""
    elements = {
        "span[name='downloadSpeedMbps']": download,
        "span[name='uploadSpeedMbps']": upload,
        "span[name='ping']": ping,
    }

    def _find(by, selector):
        el = MagicMock()
        el.text = elements.get(selector, "")
        return el

    return _find


class TestRunGoogle:
    """Tests for run_google()."""

    def test_skip_when_should_run_false(self, mock_app):
        """Skip when _should_run returns False."""
        mock_app._should_run = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_google(mock_app)
        mock_app.send_results.assert_not_called()

    def test_skip_when_load_fails(self, mock_app):
        """Skip when page load fails."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_google(mock_app)
        mock_app.send_results.assert_not_called()

    def test_sends_results_on_success(self, mock_app):
        """Send download/upload/ping data on successful measurement."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.driver.find_element.side_effect = _mock_find_element_results("250.3", "80.1", "3")

        with (
            patch("speedtest_z.sites.google.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.google.time"),
        ):
            mock_wdw.return_value.until.return_value = True
            mock_app.wait.until.return_value = MagicMock()  # start button
            run_google(mock_app)

        mock_app.send_results.assert_called_once()
        data = mock_app.send_results.call_args[0][0]
        assert len(data) == 3
        assert data[0]["key"] == "google.download"
        assert data[0]["value"] == "250.3"
        assert data[1]["key"] == "google.upload"
        assert data[1]["value"] == "80.1"
        assert data[2]["key"] == "google.ping"
        assert data[2]["value"] == "3"

    def test_start_button_not_found(self, mock_app):
        """Return early when start button is not found."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        with patch("speedtest_z.sites.google.time"):
            mock_app.wait.until.side_effect = Exception("element not clickable")
            run_google(mock_app)

        mock_app.send_results.assert_not_called()
        mock_app.take_snapshot.assert_any_call("google_error_start")

    def test_timeout_waiting_for_results(self, mock_app):
        """Return early on timeout waiting for measurement results."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        with (
            patch("speedtest_z.sites.google.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.google.time"),
        ):
            mock_app.wait.until.return_value = MagicMock()  # start button
            # First WebDriverWait: continue popup (timeout ok)
            # Second WebDriverWait: results wait (timeout = error)
            mock_wdw.return_value.until.side_effect = [
                TimeoutException(),  # continue popup
                TimeoutException(),  # results
            ]
            run_google(mock_app)

        mock_app.send_results.assert_not_called()
        mock_app.take_snapshot.assert_any_call("google_timeout")

    def test_continue_popup_clicked(self, mock_app):
        """Click the continue popup when it appears."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.driver.find_element.side_effect = _mock_find_element_results()

        continue_btn = MagicMock()

        with (
            patch("speedtest_z.sites.google.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.google.time"),
        ):
            mock_app.wait.until.return_value = MagicMock()  # start button
            mock_wdw.return_value.until.side_effect = [
                continue_btn,  # continue popup found
                True,  # results wait
            ]
            run_google(mock_app)

        continue_btn.click.assert_called_once()
        mock_app.send_results.assert_called_once()

    def test_error_reading_results(self, mock_app):
        """Return early when result elements cannot be read."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.driver.find_element.side_effect = Exception("element not found")

        with (
            patch("speedtest_z.sites.google.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.google.time"),
        ):
            mock_app.wait.until.return_value = MagicMock()  # start button
            mock_wdw.return_value.until.side_effect = [
                TimeoutException(),  # continue popup
                True,  # results wait
            ]
            run_google(mock_app)

        mock_app.send_results.assert_not_called()

    def test_snapshot_always_taken(self, mock_app):
        """Snapshot is always taken in the finally block."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.driver.find_element.side_effect = _mock_find_element_results()

        with (
            patch("speedtest_z.sites.google.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.google.time"),
        ):
            mock_app.wait.until.return_value = MagicMock()
            mock_wdw.return_value.until.side_effect = [
                TimeoutException(),
                True,
            ]
            run_google(mock_app)

        mock_app.take_snapshot.assert_any_call("google")

    def test_zabbix_host_in_data(self, mock_app):
        """Each data item includes the correct zabbix_host."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.zabbix_host = "test-host"
        mock_app.driver.find_element.side_effect = _mock_find_element_results()

        with (
            patch("speedtest_z.sites.google.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.google.time"),
        ):
            mock_app.wait.until.return_value = MagicMock()
            mock_wdw.return_value.until.side_effect = [TimeoutException(), True]
            run_google(mock_app)

        data = mock_app.send_results.call_args[0][0]
        for item in data:
            assert item["host"] == "test-host"
