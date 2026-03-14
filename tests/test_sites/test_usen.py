"""Tests for the USEN GATE 02 site runner."""

from unittest.mock import MagicMock, patch

from selenium.common.exceptions import NoSuchElementException, TimeoutException

from speedtest_z.sites.usen import run_usen


def _mock_find_element_results(download="350.5", upload="180.2", ping="4", jitter="1.2"):
    """Return a side_effect function for find_element returning result texts."""
    results = {
        "dlText": download,
        "ulText": upload,
        "pingText": ping,
        "jitText": jitter,
    }

    def _find(by, elem_id):
        if elem_id in results:
            el = MagicMock()
            el.text = results[elem_id]
            return el
        raise NoSuchElementException(f"Element {elem_id} not found")

    return _find


class TestRunUsen:
    """Tests for run_usen()."""

    def test_skip_when_should_run_false(self, mock_app):
        """Skip when _should_run returns False."""
        mock_app._should_run = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_usen(mock_app)
        mock_app.send_results.assert_not_called()

    def test_skip_when_load_fails(self, mock_app):
        """Skip when page load fails."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_usen(mock_app)
        mock_app.send_results.assert_not_called()

    def test_sends_results_on_success(self, mock_app):
        """Send download/upload/ping/jitter on success."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.driver.find_element.side_effect = _mock_find_element_results(
            "500.0", "200.0", "2", "0.5"
        )

        with (
            patch("speedtest_z.sites.usen.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.usen.time"),
        ):
            mock_app.wait.until.return_value = MagicMock()  # start button
            mock_wdw.return_value.until.return_value = True  # wait/completion
            run_usen(mock_app)

        mock_app.send_results.assert_called_once()
        data = mock_app.send_results.call_args[0][0]
        assert len(data) == 4
        assert data[0]["key"] == "usen.download"
        assert data[0]["value"] == "500.0"
        assert data[1]["key"] == "usen.upload"
        assert data[1]["value"] == "200.0"
        assert data[2]["key"] == "usen.ping"
        assert data[2]["value"] == "2"
        assert data[3]["key"] == "usen.jitter"
        assert data[3]["value"] == "0.5"

    def test_start_button_not_found(self, mock_app):
        """Return early when start button is not found."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        mock_app.wait.until.side_effect = Exception("not clickable")
        run_usen(mock_app)

        mock_app.send_results.assert_not_called()
        mock_app.take_snapshot.assert_any_call("usen_error_start")

    def test_timeout_waiting_for_completion(self, mock_app):
        """Return early on timeout waiting for completion."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        with (
            patch("speedtest_z.sites.usen.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.usen.time"),
        ):
            mock_app.wait.until.return_value = MagicMock()  # start button
            # speedtest_wait class detection (ok), then completion timeout
            mock_wdw.return_value.until.side_effect = [
                True,  # speedtest_wait appeared
                TimeoutException(),  # completion timeout
            ]
            run_usen(mock_app)

        mock_app.send_results.assert_not_called()
        mock_app.take_snapshot.assert_any_call("usen_timeout")

    def test_result_elements_not_found(self, mock_app):
        """Return early when result elements are missing from DOM."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.driver.find_element.side_effect = NoSuchElementException("not found")

        with (
            patch("speedtest_z.sites.usen.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.usen.time"),
        ):
            mock_app.wait.until.return_value = MagicMock()
            mock_wdw.return_value.until.return_value = True
            run_usen(mock_app)

        mock_app.send_results.assert_not_called()

    def test_speedtest_wait_class_not_detected(self, mock_app):
        """Continue even when speedtest_wait class does not appear."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.driver.find_element.side_effect = _mock_find_element_results()

        with (
            patch("speedtest_z.sites.usen.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.usen.time"),
        ):
            mock_app.wait.until.return_value = MagicMock()
            mock_wdw.return_value.until.side_effect = [
                TimeoutException(),  # speedtest_wait not detected (warning only)
                True,  # completion
            ]
            run_usen(mock_app)

        # Should still proceed and send results
        mock_app.send_results.assert_called_once()

    def test_snapshot_always_taken(self, mock_app):
        """Snapshot is always taken in the finally block."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.driver.find_element.side_effect = _mock_find_element_results()

        with (
            patch("speedtest_z.sites.usen.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.usen.time"),
        ):
            mock_app.wait.until.return_value = MagicMock()
            mock_wdw.return_value.until.return_value = True
            run_usen(mock_app)

        mock_app.take_snapshot.assert_any_call("usen")

    def test_zabbix_host_in_data(self, mock_app):
        """Each data item includes the correct zabbix_host."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.zabbix_host = "usen-host"
        mock_app.driver.find_element.side_effect = _mock_find_element_results()

        with (
            patch("speedtest_z.sites.usen.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.usen.time"),
        ):
            mock_app.wait.until.return_value = MagicMock()
            mock_wdw.return_value.until.return_value = True
            run_usen(mock_app)

        data = mock_app.send_results.call_args[0][0]
        for item in data:
            assert item["host"] == "usen-host"
