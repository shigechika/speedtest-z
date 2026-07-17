"""Tests for the Ookla Speedtest site runner."""

from unittest.mock import MagicMock, patch

from selenium.common.exceptions import TimeoutException

from speedtest_z.sites.ookla import run_ookla


def _result(download="250.5", upload="80.3", ping="5"):
    """Return a result dict as produced by the extraction JavaScript."""
    return {"download": download, "upload": upload, "ping": ping}


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

    def test_server_selection(self, mock_app):
        """Server selection flow when ookla_server is set."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.ookla_server = "TestServer"
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.MAX_RETRIES = 1
        mock_app.driver.execute_script.return_value = _result()

        server_elem = MagicMock()
        server_elem.text = "CurrentServer"  # different from ookla_server
        change_link = MagicMock()
        search_box = MagicMock()
        server_item = MagicMock()
        server_item.text = "TestServer - Fast"

        with (
            patch("speedtest_z.sites.ookla.WebDriverWait") as mock_wdw,
            patch("speedtest_z.sites.ookla.time"),
        ):
            mock_wdw.return_value.until.side_effect = [
                TimeoutException(),  # consent
                server_elem,  # current server element
                True,  # completion
            ]
            mock_app.wait.until.side_effect = [
                change_link,  # Change Server link
                search_box,  # host-search box
                MagicMock(),  # server list presence
                MagicMock(),  # start button
            ]
            mock_app.driver.find_elements.return_value = [server_item]
            run_ookla(mock_app)

        server_item.click.assert_called_once()

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
