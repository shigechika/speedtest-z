"""Tests for the iNonius site runner."""

from unittest.mock import MagicMock, patch

from selenium.common.exceptions import NoSuchElementException, TimeoutException

from speedtest_z.sites.inonius import _inonius_fallback_start, run_inonius


class TestInoniusFallbackStart:
    """Tests for _inonius_fallback_start()."""

    def test_fallback_returns_true_when_running(self, mock_app):
        """Return True when test is already running (cookie consent)."""
        with patch("speedtest_z.sites.inonius.WebDriverWait") as mock_wait:
            mock_wait.return_value.until.return_value = True
            result = _inonius_fallback_start(mock_app)
        assert result is True

    def test_fallback_returns_false_on_timeout(self, mock_app):
        """Return False and take snapshot on timeout."""
        mock_app.take_snapshot = MagicMock()
        with patch("speedtest_z.sites.inonius.WebDriverWait") as mock_wait:
            mock_wait.return_value.until.side_effect = TimeoutException()
            result = _inonius_fallback_start(mock_app)
        assert result is False
        mock_app.take_snapshot.assert_called_once_with("inonius_error_fallback")


class TestRunInonius:
    """Tests for run_inonius()."""

    def test_skip_when_should_run_false(self, mock_app):
        """Skip when _should_run returns False."""
        mock_app._should_run = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_inonius(mock_app)
        mock_app.send_results.assert_not_called()

    def test_skip_when_load_fails(self, mock_app):
        """Skip when page load fails."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=False)
        mock_app.send_results = MagicMock()
        run_inonius(mock_app)
        mock_app.send_results.assert_not_called()

    def test_auto_consent_clicks_button(self, mock_app):
        """Click consent/start button in auto_consent mode."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        mock_btn = MagicMock()
        mock_element = MagicMock()
        mock_element.text = "100"

        with patch("speedtest_z.sites.inonius.WebDriverWait") as mock_wait:
            mock_wait_inst = MagicMock()
            mock_wait.return_value = mock_wait_inst
            mock_wait_inst.until.side_effect = [mock_btn, True]
            mock_app.driver.find_element.return_value = mock_element

            run_inonius(mock_app)

        mock_btn.click.assert_called_once()

    def test_auto_consent_fallback_on_timeout(self, mock_app):
        """Use fallback when consent dialog times out in auto_consent mode."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        mock_element = MagicMock()
        mock_element.text = "200"

        with patch("speedtest_z.sites.inonius.WebDriverWait") as mock_wait:
            mock_wait_inst = MagicMock()
            mock_wait.return_value = mock_wait_inst
            # 1st: consent button timeout -> fallback
            # 2nd: fallback succeeds
            # 3rd: completion wait
            mock_wait_inst.until.side_effect = [
                TimeoutException(),  # consent button
                True,  # fallback check
                True,  # completion
            ]
            mock_app.driver.find_element.return_value = mock_element
            run_inonius(mock_app)

        mock_app.send_results.assert_called_once()

    def test_auto_consent_fallback_fails(self, mock_app):
        """Return early when both consent and fallback fail."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        with patch("speedtest_z.sites.inonius.WebDriverWait") as mock_wait:
            mock_wait_inst = MagicMock()
            mock_wait.return_value = mock_wait_inst
            mock_wait_inst.until.side_effect = [
                TimeoutException(),  # consent button
                TimeoutException(),  # fallback also fails
            ]
            run_inonius(mock_app)

        mock_app.send_results.assert_not_called()

    def test_manual_consent_dialog_wait(self, mock_app):
        """Wait for user to dismiss dialog in manual consent mode."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = False
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        dialog = MagicMock()
        dialog.is_displayed.return_value = False  # dialog dismissed
        mock_element = MagicMock()
        mock_element.text = "50"

        with patch("speedtest_z.sites.inonius.WebDriverWait") as mock_wait:
            mock_wait_inst = MagicMock()
            mock_wait.return_value = mock_wait_inst
            mock_wait_inst.until.side_effect = [
                dialog,  # dialog found
                True,  # dialog dismissed (lambda check)
                True,  # completion wait
            ]
            mock_app.driver.find_element.return_value = mock_element
            run_inonius(mock_app)

        mock_app.send_results.assert_called_once()

    def test_manual_consent_no_dialog_fallback(self, mock_app):
        """Use fallback when no dialog appears in manual mode."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = False
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        mock_element = MagicMock()
        mock_element.text = "75"

        with patch("speedtest_z.sites.inonius.WebDriverWait") as mock_wait:
            mock_wait_inst = MagicMock()
            mock_wait.return_value = mock_wait_inst
            mock_wait_inst.until.side_effect = [
                TimeoutException(),  # dialog not found
                True,  # fallback succeeds
                True,  # completion wait
            ]
            mock_app.driver.find_element.return_value = mock_element
            run_inonius(mock_app)

        mock_app.send_results.assert_called_once()

    def test_timeout_waiting_for_completion(self, mock_app):
        """Return early on timeout waiting for 'Test completed!'."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        with patch("speedtest_z.sites.inonius.WebDriverWait") as mock_wait:
            mock_wait_inst = MagicMock()
            mock_wait.return_value = mock_wait_inst
            mock_wait_inst.until.side_effect = [
                MagicMock(),  # consent button
                TimeoutException(),  # completion timeout
            ]
            run_inonius(mock_app)

        mock_app.send_results.assert_not_called()
        mock_app.take_snapshot.assert_any_call("inonius_timeout")

    def test_sends_all_result_keys(self, mock_app):
        """Send all 10 iNonius metrics on success."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        mock_element = MagicMock()
        mock_element.text = "100"

        with patch("speedtest_z.sites.inonius.WebDriverWait") as mock_wait:
            mock_wait_inst = MagicMock()
            mock_wait.return_value = mock_wait_inst
            mock_wait_inst.until.side_effect = [MagicMock(), True]
            mock_app.driver.find_element.return_value = mock_element
            run_inonius(mock_app)

        mock_app.send_results.assert_called_once()
        data = mock_app.send_results.call_args[0][0]
        keys = {d["key"] for d in data}
        expected_keys = {
            "inonius.IPv6_RTT",
            "inonius.IPv6_JIT",
            "inonius.IPv6_DL",
            "inonius.IPv6_UL",
            "inonius.IPv6_MSS",
            "inonius.IPv4_RTT",
            "inonius.IPv4_JIT",
            "inonius.IPv4_DL",
            "inonius.IPv4_UL",
            "inonius.IPv4_MSS",
        }
        assert keys == expected_keys

    def test_mss_parsing_splits_last_word(self, mock_app):
        """MSS values are parsed by taking the last word from text."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        def _find(by, xpath):
            el = MagicMock()
            if "div[2]/p" in xpath or "div[2]/p[1]" in xpath:
                # MSS elements have text like "MSS 1460"
                el.text = "MSS 1460"
            else:
                el.text = "50.5"
            return el

        mock_app.driver.find_element.side_effect = _find

        with patch("speedtest_z.sites.inonius.WebDriverWait") as mock_wait:
            mock_wait_inst = MagicMock()
            mock_wait.return_value = mock_wait_inst
            mock_wait_inst.until.side_effect = [MagicMock(), True]
            run_inonius(mock_app)

        data = mock_app.send_results.call_args[0][0]
        mss_items = [d for d in data if "_MSS" in d["key"]]
        for item in mss_items:
            assert item["value"] == "1460"

    def test_missing_elements_skipped(self, mock_app):
        """Missing elements are skipped without error."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        # Only IPv4_DL element exists, rest raise NoSuchElementException
        ipv4_dl_xpath = (
            "/html/body/div/astro-island/div/div[1]/div/div[1]/div[1]/div[1]/div/div/span[1]"
        )

        def _find(by, xpath):
            if xpath == ipv4_dl_xpath:
                el = MagicMock()
                el.text = "300"
                return el
            raise NoSuchElementException("not found")

        mock_app.driver.find_element.side_effect = _find

        with patch("speedtest_z.sites.inonius.WebDriverWait") as mock_wait:
            mock_wait_inst = MagicMock()
            mock_wait.return_value = mock_wait_inst
            mock_wait_inst.until.side_effect = [MagicMock(), True]
            run_inonius(mock_app)

        mock_app.send_results.assert_called_once()
        data = mock_app.send_results.call_args[0][0]
        assert len(data) == 1
        assert data[0]["key"] == "inonius.IPv4_DL"
        assert data[0]["value"] == "300"

    def test_empty_value_skipped(self, mock_app):
        """Elements with empty text are skipped."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        mock_element = MagicMock()
        mock_element.text = ""

        with patch("speedtest_z.sites.inonius.WebDriverWait") as mock_wait:
            mock_wait_inst = MagicMock()
            mock_wait.return_value = mock_wait_inst
            mock_wait_inst.until.side_effect = [MagicMock(), True]
            mock_app.driver.find_element.return_value = mock_element
            run_inonius(mock_app)

        mock_app.send_results.assert_called_once()
        data = mock_app.send_results.call_args[0][0]
        assert len(data) == 0  # all empty, none sent

    def test_snapshot_always_taken(self, mock_app):
        """Snapshot is always taken in the finally block."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()

        mock_element = MagicMock()
        mock_element.text = "100"

        with patch("speedtest_z.sites.inonius.WebDriverWait") as mock_wait:
            mock_wait_inst = MagicMock()
            mock_wait.return_value = mock_wait_inst
            mock_wait_inst.until.side_effect = [MagicMock(), True]
            mock_app.driver.find_element.return_value = mock_element
            run_inonius(mock_app)

        mock_app.take_snapshot.assert_any_call("inonius")

    def test_zabbix_host_in_data(self, mock_app):
        """Each data item includes the correct zabbix_host."""
        mock_app._should_run = MagicMock(return_value=True)
        mock_app._load_with_retry = MagicMock(return_value=True)
        mock_app.auto_consent = True
        mock_app.send_results = MagicMock()
        mock_app.take_snapshot = MagicMock()
        mock_app.zabbix_host = "inonius-host"

        mock_element = MagicMock()
        mock_element.text = "100"

        with patch("speedtest_z.sites.inonius.WebDriverWait") as mock_wait:
            mock_wait_inst = MagicMock()
            mock_wait.return_value = mock_wait_inst
            mock_wait_inst.until.side_effect = [MagicMock(), True]
            mock_app.driver.find_element.return_value = mock_element
            run_inonius(mock_app)

        data = mock_app.send_results.call_args[0][0]
        for item in data:
            assert item["host"] == "inonius-host"
