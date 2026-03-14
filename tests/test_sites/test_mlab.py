"""Tests for the M-Lab site runner."""

from unittest.mock import MagicMock, patch

from selenium.common.exceptions import TimeoutException

from speedtest_z.sites.mlab import run_mlab


def _mock_find_element_results(
    download="85.3 Mbps", upload="42.1 Mbps", latency="12 ms", retrans="0.5%"
):
    """Return a side_effect function for find_element returning result texts."""
    # M-Lab results are in a table: tr[3]=download, tr[4]=upload, tr[5]=latency, tr[6]=retrans
    results = {}
    base = '//*[@id="measurementSpace"]//table/tbody'
    results[f"{base}/tr[3]/td[3]/strong"] = download
    results[f"{base}/tr[4]/td[3]/strong"] = upload
    results[f"{base}/tr[5]/td[3]/strong"] = latency
    results[f"{base}/tr[6]/td[3]/strong"] = retrans

    def _find(by, xpath):
        el = MagicMock()
        el.text = results.get(xpath, "")
        return el

    return _find


class TestRunMlab:
    """Tests for run_mlab()."""

    def test_skip_when_should_run_false(self, mock_app):
        """Skip when _should_run returns False."""
        mock_app._should_run = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_mlab(mock_app)
        mock_app.send_results.assert_not_called()

    def test_skip_when_load_fails(self, mock_app):
        """Skip when page load fails."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_mlab(mock_app)
        mock_app.send_results.assert_not_called()

    def test_sends_results_on_success(self, mock_app):
        """Send download/upload/latency/retrans on success."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.driver.find_element.side_effect = _mock_find_element_results(
            "120.5 Mbps", "55.0 Mbps", "8 ms", "1.2%"
        )

        with patch("speedtest_z.sites.mlab.WebDriverWait") as mock_wdw:
            mock_app.wait.until.side_effect = [
                MagicMock(),  # consent checkbox
                MagicMock(),  # start button
            ]
            mock_wdw.return_value.until.return_value = True  # completion wait
            run_mlab(mock_app)

        mock_app.send_results.assert_called_once()
        data = mock_app.send_results.call_args[0][0]
        assert len(data) == 4
        assert data[0]["key"] == "mlab.download"
        assert data[0]["value"] == "120.5"
        assert data[1]["key"] == "mlab.upload"
        assert data[1]["value"] == "55.0"
        assert data[2]["key"] == "mlab.latency"
        assert data[2]["value"] == "8"
        assert data[3]["key"] == "mlab.retrans"
        assert data[3]["value"] == "1.2"

    def test_result_parsing_splits_on_whitespace(self, mock_app):
        """Result text is split on whitespace to extract numeric value."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.driver.find_element.side_effect = _mock_find_element_results(
            "200.0 Mbps", "100.0 Mbps", "5 ms", "0.0%"
        )

        with patch("speedtest_z.sites.mlab.WebDriverWait") as mock_wdw:
            mock_app.wait.until.side_effect = [MagicMock(), MagicMock()]
            mock_wdw.return_value.until.return_value = True
            run_mlab(mock_app)

        data = mock_app.send_results.call_args[0][0]
        # retrans: "0.0%" -> "0.0" (% removed, then stripped)
        assert data[3]["value"] == "0.0"

    def test_auto_consent_checkbox_clicked(self, mock_app):
        """Consent checkbox is clicked in auto_consent mode."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.driver.find_element.side_effect = _mock_find_element_results()

        chk_box = MagicMock()
        with patch("speedtest_z.sites.mlab.WebDriverWait") as mock_wdw:
            mock_app.wait.until.side_effect = [
                chk_box,  # consent checkbox
                MagicMock(),  # start button
            ]
            mock_wdw.return_value.until.return_value = True
            run_mlab(mock_app)

        mock_app.driver.execute_script.assert_called_once()

    def test_start_button_error_returns_early(self, mock_app):
        """Return early when start button is not clickable."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        with patch("speedtest_z.sites.mlab.WebDriverWait"):
            mock_app.wait.until.side_effect = [
                MagicMock(),  # consent checkbox
                Exception("not clickable"),  # start button
            ]
            run_mlab(mock_app)

        mock_app.send_results.assert_not_called()
        mock_app.take_snapshot.assert_any_call("mlab_error_start")

    def test_timeout_waiting_for_results(self, mock_app):
        """Return early on timeout waiting for 'Again' button."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        with patch("speedtest_z.sites.mlab.WebDriverWait") as mock_wdw:
            mock_app.wait.until.side_effect = [MagicMock(), MagicMock()]
            mock_wdw.return_value.until.side_effect = TimeoutException()
            run_mlab(mock_app)

        mock_app.send_results.assert_not_called()
        mock_app.take_snapshot.assert_any_call("mlab_timeout")

    def test_error_extracting_results(self, mock_app):
        """Return early when result elements raise an exception."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.driver.find_element.side_effect = Exception("element not found")

        with patch("speedtest_z.sites.mlab.WebDriverWait") as mock_wdw:
            mock_app.wait.until.side_effect = [MagicMock(), MagicMock()]
            mock_wdw.return_value.until.return_value = True
            run_mlab(mock_app)

        mock_app.send_results.assert_not_called()

    def test_snapshot_always_taken(self, mock_app):
        """Snapshot is always taken in the finally block."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.driver.find_element.side_effect = _mock_find_element_results()

        with patch("speedtest_z.sites.mlab.WebDriverWait") as mock_wdw:
            mock_app.wait.until.side_effect = [MagicMock(), MagicMock()]
            mock_wdw.return_value.until.return_value = True
            run_mlab(mock_app)

        mock_app.take_snapshot.assert_any_call("mlab")

    def test_manual_consent_mode(self, mock_app):
        """In manual consent mode, wait for user to check the checkbox."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = False
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.driver.find_element.side_effect = _mock_find_element_results()

        chk_box = MagicMock()
        chk_box.is_selected.return_value = False

        with patch("speedtest_z.sites.mlab.WebDriverWait") as mock_wdw:
            # First WDW(5): checkbox found, second WDW(120): user checks it
            # Third WDW(90): completion wait
            mock_wdw_inst = MagicMock()
            mock_wdw.return_value = mock_wdw_inst
            mock_wdw_inst.until.side_effect = [chk_box, True, True]
            mock_app.wait.until.return_value = MagicMock()  # start button
            run_mlab(mock_app)

        mock_app.send_results.assert_called_once()
