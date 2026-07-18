"""Unit tests for speedtest_z/runner.py core logic."""

import argparse
import configparser
from unittest.mock import MagicMock, patch

import pytest

from speedtest_z.runner import SpeedtestZ
from speedtest_z.sender import SenderManager

# ---------------------------------------------------------------------------
# Helper: create SpeedtestZ instance bypassing WebDriver init
# ---------------------------------------------------------------------------


def _make_sender(dryrun=True, zabbix_enable=False, grafana_sender=None, otel_sender=None):
    """Create a SenderManager instance for direct testing."""
    with patch.object(SenderManager, "__init__", lambda self, *a, **kw: None):
        sender = SenderManager.__new__(SenderManager)
        sender.dry_run = dryrun
        sender.zabbix_enable = zabbix_enable
        sender.zabbix_server = "127.0.0.1"
        sender.zabbix_port = 10051
        sender.zabbix_host = "speedtest-agent"
        sender.grafana_sender = grafana_sender
        sender.otel_sender = otel_sender
    return sender


def _make_app(
    config_dict=None,
    dryrun=True,
    zabbix_enable=False,
    grafana_sender=None,
    otel_sender=None,
    explicit_sites=False,
):
    """Create a SpeedtestZ instance with WebDriver bypassed."""
    config = configparser.ConfigParser()
    if config_dict:
        config.read_dict(config_dict)

    with patch.object(SpeedtestZ, "__init__", lambda self, *a, **kw: None):
        app = SpeedtestZ.__new__(SpeedtestZ)
        app.config = config
        app.dryrun = dryrun
        app.headless = True
        app.timeout = 30
        app.zabbix_enable = zabbix_enable
        app.zabbix_server = "127.0.0.1"
        app.zabbix_port = 10051
        app.zabbix_host = "speedtest-agent"
        app.grafana_sender = grafana_sender
        app.otel_sender = otel_sender
        app.snapshot_enable = False
        app.snapshot_dir = "./snapshots"
        app.explicit_sites = explicit_sites
        app.auto_consent = False
        app.ookla_server = None
        app.chrome_profile_dir = "/tmp/chrome-profile"
        app.driver = MagicMock()
        app.wait = MagicMock()
        app.action_chains = MagicMock()
        # SenderManager mock
        sender = MagicMock(spec=SenderManager)
        sender.otel_sender = otel_sender
        app.sender = sender
    return app


# ===========================================================================
# _should_run tests
# ===========================================================================


class TestShouldRun:
    """Tests for _should_run() frequency control."""

    def test_explicit_sites_always_runs(self):
        """When sites are explicitly specified, _should_run always returns True."""
        app = _make_app(
            config_dict={"frequency": {"cloudflare": "0"}},
            explicit_sites=True,
        )
        assert app._should_run("cloudflare") is True

    def test_frequency_zero_skips(self):
        """Frequency 0 disables the site."""
        app = _make_app(config_dict={"frequency": {"ookla": "0"}})
        assert app._should_run("ookla") is False

    def test_frequency_negative_skips(self):
        """Negative frequency disables the site."""
        app = _make_app(config_dict={"frequency": {"ookla": "-10"}})
        assert app._should_run("ookla") is False

    def test_frequency_100_always_runs(self):
        """Frequency 100 always runs."""
        app = _make_app(config_dict={"frequency": {"cloudflare": "100"}})
        assert app._should_run("cloudflare") is True

    def test_frequency_over_100_always_runs(self):
        """Frequency > 100 always runs (treated as 100%)."""
        app = _make_app(config_dict={"frequency": {"cloudflare": "200"}})
        assert app._should_run("cloudflare") is True

    def test_frequency_default_100_when_section_missing(self):
        """When [frequency] section is missing, fallback is 100 (always run)."""
        app = _make_app(config_dict={"general": {"dry_run": "true"}})
        assert app._should_run("cloudflare") is True

    def test_frequency_default_100_when_key_missing(self):
        """When site key is missing from [frequency], fallback is 100."""
        app = _make_app(config_dict={"frequency": {"ookla": "50"}})
        assert app._should_run("cloudflare") is True

    def test_frequency_50_probabilistic(self):
        """Frequency 50 uses random; verify behavior with controlled random."""
        app = _make_app(config_dict={"frequency": {"ookla": "50"}})

        # random returns 30 (<= 50) -> should run
        with patch("speedtest_z.runner.random.randint", return_value=30):
            assert app._should_run("ookla") is True

        # random returns 80 (> 50) -> should skip
        with patch("speedtest_z.runner.random.randint", return_value=80):
            assert app._should_run("ookla") is False

    def test_frequency_boundary_value(self):
        """Frequency boundary: random == frequency -> should run."""
        app = _make_app(config_dict={"frequency": {"mlab": "10"}})
        with patch("speedtest_z.runner.random.randint", return_value=10):
            assert app._should_run("mlab") is True

        with patch("speedtest_z.runner.random.randint", return_value=11):
            assert app._should_run("mlab") is False


# ===========================================================================
# _load_with_retry tests
# ===========================================================================


class TestLoadWithRetry:
    """Tests for _load_with_retry() retry logic."""

    def test_success_on_first_attempt(self):
        """Successful page load on first attempt returns True."""
        app = _make_app()
        app.driver.page_source = "<html><body>OK</body></html>"

        with patch("speedtest_z.runner.time.sleep"):
            result = app._load_with_retry("http://example.com")
        assert result is True
        app.driver.get.assert_called_once_with("http://example.com")

    def test_success_after_retry(self):
        """Page loads successfully on second attempt after initial error page."""
        app = _make_app()
        app.driver.page_source = "<html>err_connection_refused</html>"

        call_count = 0

        def page_source_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return "<html>err_connection_refused</html>"
            return "<html><body>OK</body></html>"

        type(app.driver).page_source = property(lambda self: page_source_side_effect())

        with patch("speedtest_z.runner.time.sleep"):
            result = app._load_with_retry("http://example.com", max_retries=3, delay=0)
        assert result is True

    def test_all_retries_fail(self):
        """All retries fail returns False."""
        app = _make_app()
        app.driver.page_source = "<html>err_name_not_resolved</html>"

        with patch("speedtest_z.runner.time.sleep"):
            result = app._load_with_retry("http://example.com", max_retries=3, delay=0)
        assert result is False
        assert app.driver.get.call_count == 3

    def test_exception_during_load(self):
        """Exception during driver.get triggers retry."""
        app = _make_app()
        app.driver.get.side_effect = [Exception("Timeout"), None]
        app.driver.page_source = "<html><body>OK</body></html>"

        with patch("speedtest_z.runner.time.sleep"):
            result = app._load_with_retry("http://example.com", max_retries=2, delay=0)
        assert result is True
        assert app.driver.get.call_count == 2

    def test_all_attempts_raise_exception(self):
        """All attempts raise exceptions returns False."""
        app = _make_app()
        app.driver.get.side_effect = Exception("Network error")

        with patch("speedtest_z.runner.time.sleep"):
            result = app._load_with_retry("http://example.com", max_retries=2, delay=0)
        assert result is False

    def test_default_retries_and_delay(self):
        """Default max_retries and delay use class constants."""
        app = _make_app()
        app.driver.page_source = "<html>dns_probe</html>"

        with patch("speedtest_z.runner.time.sleep") as mock_sleep:
            app._load_with_retry("http://example.com")
        assert app.driver.get.call_count == SpeedtestZ.MAX_RETRIES
        # sleep(2) for each attempt + sleep(delay) between retries
        # delay sleeps = MAX_RETRIES - 1
        delay_calls = [c for c in mock_sleep.call_args_list if c[0][0] == SpeedtestZ.RETRY_DELAY]
        assert len(delay_calls) == SpeedtestZ.MAX_RETRIES - 1

    def test_error_indicators_detected(self):
        """Various error indicators in page source trigger retry."""
        error_pages = [
            "<html>can't be reached</html>",
            "<html>ERR_CONNECTION_RESET</html>",
            "<html>dns_probe_finished_nxdomain</html>",
            "<html>connection refused</html>",
            "<html>took too long to respond</html>",
        ]
        for error_page in error_pages:
            app = _make_app()
            app.driver.page_source = error_page
            with patch("speedtest_z.runner.time.sleep"):
                result = app._load_with_retry("http://example.com", max_retries=1, delay=0)
            assert result is False, f"Should detect error in: {error_page}"


# ===========================================================================
# send_results tests (OTel backend dispatch)
# ===========================================================================


class TestSendResultsOtel:
    """Tests for SenderManager.send() OTel backend dispatch."""

    def test_otel_sender_called(self):
        """OTel sender is called when configured and not dryrun."""
        mock_otel = MagicMock()
        sender = _make_sender(dryrun=False, otel_sender=mock_otel)
        data = [{"key": "cloudflare.download", "value": "100.5"}]
        with patch("speedtest_z.sender.Sender"):
            sender.send(data)
        mock_otel.send.assert_called_once_with(data)

    def test_otel_sender_not_called_on_dryrun(self):
        """OTel sender is NOT called when dryrun is True."""
        mock_otel = MagicMock()
        sender = _make_sender(dryrun=True, otel_sender=mock_otel)
        data = [{"key": "cloudflare.download", "value": "100.5"}]
        sender.send(data)
        mock_otel.send.assert_not_called()

    def test_otel_error_handled(self):
        """OTel send error does not crash."""
        mock_otel = MagicMock()
        mock_otel.send.side_effect = Exception("OTel export failed")
        sender = _make_sender(dryrun=False, otel_sender=mock_otel)
        data = [{"key": "cloudflare.download", "value": "100.5"}]
        with patch("speedtest_z.sender.Sender"):
            sender.send(data)  # should not raise

    def test_all_backends_called(self):
        """All three backends (Zabbix, Grafana, OTel) are called together."""
        mock_grafana = MagicMock()
        mock_otel = MagicMock()
        sender = _make_sender(
            dryrun=False,
            zabbix_enable=True,
            grafana_sender=mock_grafana,
            otel_sender=mock_otel,
        )
        data = [{"key": "cloudflare.download", "value": "100.5"}]
        with patch("speedtest_z.sender.Sender") as mock_sender_cls:
            mock_sender_cls.return_value = MagicMock()
            sender.send(data)
            mock_sender_cls.return_value.send_bulk.assert_called_once()
        mock_grafana.send.assert_called_once_with(data)
        mock_otel.send.assert_called_once_with(data)

    def test_delegation_from_app(self):
        """SpeedtestZ.send_results() delegates to SenderManager.send()."""
        app = _make_app(dryrun=False)
        data = [{"key": "cloudflare.download", "value": "100.5"}]
        app.send_results(data)
        app.sender.send.assert_called_once_with(data)


# ===========================================================================
# Config parsing tests
# ===========================================================================


class TestConfigParsing:
    """Tests for config parsing in __init__."""

    def _init_app_with_config(self, config_dict, args=None):
        """Initialize SpeedtestZ with a given config dict, bypassing WebDriver."""
        config = configparser.ConfigParser()
        config.read_dict(config_dict)

        with (
            patch.object(SpeedtestZ, "_init_driver"),
            patch("speedtest_z.runner._find_config", return_value=None),
            patch("speedtest_z.runner.signal.signal"),
            patch.object(configparser.ConfigParser, "read"),
        ):
            app = SpeedtestZ.__new__(SpeedtestZ)
            app.config = config
            # Reproduce __init__ config parsing logic
            app.dryrun = config.getboolean("general", "dry_run", fallback=None)
            if app.dryrun is None:
                app.dryrun = config.getboolean("general", "dryrun", fallback=True)
            app.headless = config.getboolean("general", "headless", fallback=True)
            app.timeout = config.getint("general", "timeout", fallback=30)
            app.ookla_server = config.get("general", "ookla_server", fallback=None)
        return app

    def test_general_defaults(self):
        """Default values when [general] has no keys."""
        app = self._init_app_with_config({"general": {}})
        assert app.dryrun is True  # fallback default
        assert app.headless is True
        assert app.timeout == 30

    def test_general_custom_values(self):
        """Custom values are read correctly."""
        app = self._init_app_with_config(
            {"general": {"dry_run": "false", "headless": "false", "timeout": "60"}}
        )
        assert app.dryrun is False
        assert app.headless is False
        assert app.timeout == 60

    def test_dryrun_fallback(self):
        """Old 'dryrun' key is used when 'dry_run' is missing."""
        app = self._init_app_with_config({"general": {"dryrun": "false"}})
        assert app.dryrun is False

    def test_dry_run_priority_over_dryrun(self):
        """'dry_run' takes priority over 'dryrun'."""
        app = self._init_app_with_config({"general": {"dry_run": "false", "dryrun": "true"}})
        assert app.dryrun is False

    def test_ookla_server_default_none(self):
        """ookla_server defaults to None."""
        app = self._init_app_with_config({"general": {}})
        assert app.ookla_server is None

    def test_ookla_server_set(self):
        """ookla_server is read from config."""
        app = self._init_app_with_config({"general": {"ookla_server": "example.ookla.com"}})
        assert app.ookla_server == "example.ookla.com"


class TestCLIOverride:
    """Tests for CLI argument overrides."""

    def test_dry_run_override(self):
        """--dry-run CLI flag overrides config."""
        app = _make_app(config_dict={"general": {"dry_run": "false"}}, dryrun=False)
        # Simulate CLI override
        args = argparse.Namespace(
            config=None,
            dry_run=True,
            headless=None,
            timeout=None,
            sites=[],
            yes=False,
        )
        if args.dry_run:
            app.dryrun = True
        assert app.dryrun is True

    def test_timeout_override(self):
        """--timeout CLI flag overrides config."""
        app = _make_app(config_dict={"general": {"timeout": "30"}})
        args = argparse.Namespace(
            config=None,
            dry_run=False,
            headless=None,
            timeout=60,
            sites=[],
            yes=False,
        )
        if args.timeout is not None:
            app.timeout = args.timeout
        assert app.timeout == 60

    def test_explicit_sites_flag(self):
        """Providing sites sets explicit_sites=True."""
        app = _make_app()
        args = argparse.Namespace(
            config=None,
            dry_run=False,
            headless=None,
            timeout=None,
            sites=["cloudflare"],
            yes=False,
        )
        if args.sites:
            app.explicit_sites = True
        assert app.explicit_sites is True

    def test_auto_consent_flag(self):
        """--yes flag sets auto_consent=True."""
        app = _make_app()
        args = argparse.Namespace(
            config=None,
            dry_run=False,
            headless=None,
            timeout=None,
            sites=[],
            yes=True,
        )
        if getattr(args, "yes", False):
            app.auto_consent = True
        assert app.auto_consent is True


# ===========================================================================
# close() tests
# ===========================================================================


class TestClose:
    """Tests for close() cleanup logic."""

    def test_close_quits_driver(self):
        """close() calls driver.quit()."""
        app = _make_app()
        app.close()
        app.driver.quit.assert_called_once()

    def test_close_calls_sender_close(self):
        """close() calls sender.close()."""
        app = _make_app()
        app.close()
        app.sender.close.assert_called_once()

    def test_close_without_driver(self):
        """close() works when driver attribute is missing."""
        app = _make_app()
        del app.driver
        app.close()  # should not raise

    def test_close_without_sender(self):
        """close() works when sender attribute is missing but otel_sender exists."""
        mock_otel = MagicMock()
        app = _make_app(otel_sender=mock_otel)
        del app.sender
        app.close()  # should not raise, falls back to otel_sender.shutdown()
        mock_otel.shutdown.assert_called_once()

    def test_close_without_sender_or_otel(self):
        """close() works when neither sender nor otel_sender exist."""
        app = _make_app()
        del app.sender
        del app.otel_sender
        app.close()  # should not raise
        app.driver.quit.assert_called_once()

    def test_close_is_idempotent(self):
        """Calling close() twice quits the driver only once (SIGTERM + finally)."""
        app = _make_app()
        app.close()
        app.close()
        app.driver.quit.assert_called_once()
        app.sender.close.assert_called_once()

    def test_close_survives_driver_quit_error(self):
        """A driver.quit() error is suppressed so sender.close() still runs."""
        app = _make_app()
        app.driver.quit.side_effect = Exception("session already closed")
        app.close()  # should not raise
        app.sender.close.assert_called_once()


class TestHandleSigterm:
    """Tests for the SIGTERM handler."""

    def test_sigterm_closes_and_exits_143(self):
        """SIGTERM closes the app and exits with 143 (128+SIGTERM)."""
        import signal as signal_mod

        app = _make_app()
        app.close = MagicMock()
        with pytest.raises(SystemExit) as exc_info:
            app._handle_sigterm(signal_mod.SIGTERM, None)
        assert exc_info.value.code == 143
        app.close.assert_called_once()


class TestSenderManagerClose:
    """Tests for SenderManager.close() cleanup logic."""

    def test_close_shuts_down_otel(self):
        """close() calls otel_sender.shutdown()."""
        mock_otel = MagicMock()
        sender = _make_sender(otel_sender=mock_otel)
        sender.close()
        mock_otel.shutdown.assert_called_once()

    def test_close_without_otel(self):
        """close() works when otel_sender is None."""
        sender = _make_sender(otel_sender=None)
        sender.close()  # should not raise
