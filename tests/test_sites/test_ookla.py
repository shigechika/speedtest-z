"""Tests for the Ookla Speedtest site runner."""

from unittest.mock import MagicMock, patch

from selenium.common.exceptions import TimeoutException

from speedtest_z.sites.ookla import _clean_number, _select_server, run_ookla


def _result(download="250.5", upload="80.3", ping="5"):
    """Return a result dict as produced by the extraction JavaScript."""
    return {"download": download, "upload": upload, "ping": ping}


class TestCleanNumber:
    """Tests for _clean_number()."""

    def test_plain_number_passes_through(self):
        assert _clean_number("92.98") == "92.98"
        assert _clean_number("17") == "17"

    def test_thousands_separator_stripped(self):
        assert _clean_number("1,053.9") == "1053.9"

    def test_unit_suffix_stripped(self):
        assert _clean_number("92.98 Mbps") == "92.98"

    def test_non_numeric_rejected(self):
        assert _clean_number("") == ""
        assert _clean_number("—") == ""
        assert _clean_number("Mbps") == ""


class TestSelectServer:
    """Tests for _select_server() against the redesigned server dialog."""

    def _app(self, server="TestServer"):
        """Build a minimal mock app with ookla_server set."""
        app = MagicMock()
        app.ookla_server = server
        return app

    def test_noop_when_server_unset(self):
        """Nothing happens when ookla_server is not configured."""
        app = self._app(server=None)
        with patch("speedtest_z.sites.ookla.WebDriverWait") as mock_wdw:
            _select_server(app)
        mock_wdw.assert_not_called()

    def test_skips_dialog_when_already_selected(self):
        """The dialog is closed without searching when the server matches."""
        app = self._app()
        change_btn = MagicMock()
        dialog = MagicMock()
        dialog.text = "TESTSERVER Tokyo Select Automatically"
        with patch("speedtest_z.sites.ookla.WebDriverWait") as mock_wdw:
            mock_wdw.return_value.until.side_effect = [change_btn, dialog]
            _select_server(app)
        change_btn.click.assert_called_once()
        dialog.find_element.assert_not_called()

    def test_searches_and_selects_matching_row(self):
        """The row whose text contains ookla_server is clicked."""
        app = self._app()
        change_btn = MagicMock()
        dialog = MagicMock()
        dialog.text = "OtherServer Tokyo Select Automatically"
        search_box = MagicMock()
        dialog.find_element.return_value = search_box
        row_other = MagicMock()
        row_other.text = "Osaka - OtherServer"
        row_match = MagicMock()
        row_match.text = "Tokyo - TestServer 400G"
        with patch("speedtest_z.sites.ookla.WebDriverWait") as mock_wdw:
            mock_wdw.return_value.until.side_effect = [
                change_btn,  # Change Server button
                dialog,  # dialog visible
                [row_other, row_match],  # server rows
            ]
            _select_server(app)
        search_box.send_keys.assert_called_once_with("TestServer")
        row_match.click.assert_called_once()
        row_other.click.assert_not_called()

    def test_falls_back_to_first_row_without_match(self):
        """The first row is clicked when no row text matches."""
        app = self._app()
        change_btn = MagicMock()
        dialog = MagicMock()
        dialog.text = "OtherServer Tokyo"
        dialog.find_element.return_value = MagicMock()
        row1 = MagicMock()
        row1.text = "Osaka - Alpha"
        row2 = MagicMock()
        row2.text = "Nagoya - Beta"
        with patch("speedtest_z.sites.ookla.WebDriverWait") as mock_wdw:
            mock_wdw.return_value.until.side_effect = [change_btn, dialog, [row1, row2]]
            _select_server(app)
        row1.click.assert_called_once()

    def test_failure_is_nonfatal(self):
        """A missing Change Server button logs a warning and returns."""
        app = self._app()
        with patch("speedtest_z.sites.ookla.WebDriverWait") as mock_wdw:
            mock_wdw.return_value.until.side_effect = TimeoutException()
            _select_server(app)  # must not raise


class TestRunOokla:
    """Tests for run_ookla()."""

    def test_skip_when_should_run_false(self, mock_app):
        """Skip when _should_run returns False."""
        mock_app._should_run = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_ookla(mock_app)
        mock_app.send_results.assert_not_called()

    def test_skip_when_load_fails(self, mock_app):
        """Skip when page load fails."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_ookla(mock_app)
        mock_app.send_results.assert_not_called()

    def test_sends_results_on_success(self, mock_app):
        """Send download/upload/ping on success."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.ookla_server = None
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.MAX_RETRIES = 3
        mock_app.driver.execute_script.return_value = _result("300.0", "95.5", "3")

        with (
            patch("speedtest_z.sites.ookla.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.ookla.time"),
        ):
            mock_wdw.return_value.until.side_effect = [
                TimeoutException(),  # consent dialog not found
                True,  # completion (URL changed to /result/<id>)
            ]
            mock_app.wait.until.return_value = MagicMock()  # start button
            run_ookla(mock_app)

        mock_app.send_results.assert_called_once()
        data = mock_app.send_results.call_args[0][0]
        assert len(data) == 3
        assert data[0]["key"] == "ookla.download"
        assert data[0]["value"] == "300.0"
        assert data[1]["key"] == "ookla.upload"
        assert data[1]["value"] == "95.5"
        assert data[2]["key"] == "ookla.ping"
        assert data[2]["value"] == "3"

    def test_start_button_error_retries(self, mock_app):
        """Retry when start button click fails, reloading the top page."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.ookla_server = None
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.MAX_RETRIES = 2

        with (
            patch("speedtest_z.sites.ookla.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.ookla.time"),
        ):
            mock_wdw.return_value.until.side_effect = TimeoutException()
            # Start button fails on all attempts
            mock_app.wait.until.side_effect = Exception("not clickable")
            run_ookla(mock_app)

        mock_app.send_results.assert_not_called()
        # Each attempt loads the top page (refresh would stay on /result/<id>)
        assert mock_app._load_with_retry.call_count == 2

    def test_comma_separated_values_normalized(self, mock_app):
        """Thousands separators are stripped before sending to Zabbix."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.ookla_server = None
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.MAX_RETRIES = 1
        mock_app.driver.execute_script.return_value = _result("1,053.9", "1,002.1", "8.4")

        with (
            patch("speedtest_z.sites.ookla.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.ookla.time"),
        ):
            mock_wdw.return_value.until.side_effect = [TimeoutException(), True]
            mock_app.wait.until.return_value = MagicMock()
            run_ookla(mock_app)

        data = mock_app.send_results.call_args[0][0]
        assert data[0]["value"] == "1053.9"
        assert data[1]["value"] == "1002.1"
        assert data[2]["value"] == "8.4"

    def test_missing_ping_sends_throughput_only(self, mock_app):
        """A missing ping does not fail the run; download/upload still send."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.ookla_server = None
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.MAX_RETRIES = 1
        mock_app.driver.execute_script.return_value = _result("300.0", "95.5", None)

        with (
            patch("speedtest_z.sites.ookla.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.ookla.time"),
        ):
            mock_wdw.return_value.until.side_effect = [TimeoutException(), True]
            mock_app.wait.until.return_value = MagicMock()
            run_ookla(mock_app)

        data = mock_app.send_results.call_args[0][0]
        assert [d["key"] for d in data] == ["ookla.download", "ookla.upload"]

    def test_invalid_result_triggers_retry(self, mock_app):
        """Retry when the result page yields no numeric download value."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.ookla_server = None
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.MAX_RETRIES = 2
        mock_app.driver.execute_script.side_effect = [
            _result(download="", upload="", ping=""),  # 1st attempt: parse failure
            _result("300.0", "95.5", "3"),  # 2nd attempt: success
        ]

        with (
            patch("speedtest_z.sites.ookla.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.ookla.time"),
        ):
            mock_wdw.return_value.until.side_effect = [
                TimeoutException(),  # consent 1st attempt
                True,  # completion 1st attempt
                TimeoutException(),  # consent 2nd attempt
                True,  # completion 2nd attempt
            ]
            mock_app.wait.until.return_value = MagicMock()  # start button
            run_ookla(mock_app)

        mock_app.send_results.assert_called_once()
        mock_app.take_snapshot.assert_any_call("ookla_error_parse_1")

    def test_timeout_triggers_retry(self, mock_app):
        """Retry when timeout occurs waiting for the result URL."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.ookla_server = None
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.MAX_RETRIES = 2

        with (
            patch("speedtest_z.sites.ookla.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.ookla.time"),
        ):
            mock_wdw.return_value.until.side_effect = [
                TimeoutException(),  # consent 1st
                TimeoutException(),  # completion timeout 1st
                TimeoutException(),  # consent 2nd
                TimeoutException(),  # completion timeout 2nd
            ]
            mock_app.wait.until.return_value = MagicMock()
            run_ookla(mock_app)

        mock_app.send_results.assert_not_called()
        mock_app.take_snapshot.assert_any_call("ookla_timeout_1")
        mock_app.take_snapshot.assert_any_call("ookla_timeout_2")

    def test_all_retries_exhausted(self, mock_app):
        """Log error after all retries are exhausted."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.ookla_server = None
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.MAX_RETRIES = 1

        with (
            patch("speedtest_z.sites.ookla.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.ookla.time"),
        ):
            mock_wdw.return_value.until.side_effect = [
                TimeoutException(),  # consent
                TimeoutException(),  # completion timeout
            ]
            mock_app.wait.until.return_value = MagicMock()
            run_ookla(mock_app)

        mock_app.send_results.assert_not_called()

    def test_consent_auto_accepted(self, mock_app):
        """Consent banner is auto-accepted when auto_consent is True."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.ookla_server = None
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.MAX_RETRIES = 1
        mock_app.driver.execute_script.side_effect = [
            None,  # consent click
            _result(),  # result extraction
        ]

        consent_btn = MagicMock()
        with (
            patch("speedtest_z.sites.ookla.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.ookla.time"),
        ):
            mock_wdw.return_value.until.side_effect = [
                consent_btn,  # consent dialog found
                True,  # completion
            ]
            mock_app.wait.until.return_value = MagicMock()
            run_ookla(mock_app)

        first_call = mock_app.driver.execute_script.call_args_list[0]
        assert first_call[0] == ("arguments[0].click();", consent_btn)
        mock_app.send_results.assert_called_once()

    def test_manual_consent_mode(self, mock_app):
        """In manual consent mode, wait for user to dismiss banner."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = False
        mock_app.ookla_server = None
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.MAX_RETRIES = 1
        mock_app.driver.execute_script.return_value = _result()

        banner = MagicMock()
        with (
            patch("speedtest_z.sites.ookla.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.ookla.time"),
        ):
            mock_wdw.return_value.until.side_effect = [
                banner,  # banner visible
                True,  # banner dismissed
                True,  # completion
            ]
            mock_app.wait.until.return_value = MagicMock()
            run_ookla(mock_app)

        mock_app.send_results.assert_called_once()

    def test_server_selection_invoked_when_configured(self, mock_app):
        """_select_server is called once when ookla_server is set."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.ookla_server = "TestServer"
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.MAX_RETRIES = 1
        mock_app.driver.execute_script.return_value = _result()

        with (
            patch("speedtest_z.sites.ookla.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.ookla.time"),
            patch("speedtest_z.sites.ookla._select_server") as mock_select,
        ):
            mock_wdw.return_value.until.side_effect = [
                TimeoutException(),  # consent
                True,  # completion
            ]
            mock_app.wait.until.return_value = MagicMock()
            run_ookla(mock_app)

        mock_select.assert_called_once_with(mock_app)
        mock_app.send_results.assert_called_once()

    def test_zabbix_host_in_data(self, mock_app):
        """Each data item includes the correct zabbix_host."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.ookla_server = None
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.MAX_RETRIES = 1
        mock_app.zabbix_host = "my-host"
        mock_app.driver.execute_script.return_value = _result()

        with (
            patch("speedtest_z.sites.ookla.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.ookla.time"),
        ):
            mock_wdw.return_value.until.side_effect = [
                TimeoutException(),
                True,
            ]
            mock_app.wait.until.return_value = MagicMock()
            run_ookla(mock_app)

        data = mock_app.send_results.call_args[0][0]
        for item in data:
            assert item["host"] == "my-host"
