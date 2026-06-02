"""Tests for throttling (_should_run)."""

from unittest.mock import patch

from speedtest_z.runner import SpeedtestZ


def _make_app(mock_config, explicit_sites=False):
    """Create a SpeedtestZ instance, bypassing the WebDriver."""
    with patch.object(SpeedtestZ, "__init__", lambda self, *a, **kw: None):
        app = SpeedtestZ.__new__(SpeedtestZ)
        app.config = mock_config
        app.explicit_sites = explicit_sites
    return app


class TestShouldRun:
    """Tests for _should_run()."""

    def test_explicit_sites_always_true(self, mock_config):
        """Always True when sites are explicitly specified on the CLI."""
        app = _make_app(mock_config, explicit_sites=True)
        assert app._should_run("cloudflare") is True
        assert app._should_run("mlab") is True

    def test_frequency_100(self, mock_config):
        """frequency=100 always runs."""
        app = _make_app(mock_config)
        # cloudflare is 100 in the config
        assert app._should_run("cloudflare") is True

    def test_frequency_0(self, mock_config):
        """frequency=0 always skips."""
        mock_config.set("frequency", "cloudflare", "0")
        app = _make_app(mock_config)
        assert app._should_run("cloudflare") is False

    def test_frequency_50_run(self, mock_config):
        """frequency=50 runs when the random number is in range."""
        app = _make_app(mock_config)
        # ookla is 50 in the config
        with patch("speedtest_z.runner.random.randint", return_value=30):
            assert app._should_run("ookla") is True

    def test_frequency_50_skip(self, mock_config):
        """frequency=50 skips when the random number is out of range."""
        app = _make_app(mock_config)
        with patch("speedtest_z.runner.random.randint", return_value=80):
            assert app._should_run("ookla") is False

    def test_frequency_boundary_run(self, mock_config):
        """frequency=50 runs when the random number is exactly 50."""
        app = _make_app(mock_config)
        with patch("speedtest_z.runner.random.randint", return_value=50):
            assert app._should_run("ookla") is True

    def test_frequency_boundary_skip(self, mock_config):
        """frequency=50 skips when the random number is 51."""
        app = _make_app(mock_config)
        with patch("speedtest_z.runner.random.randint", return_value=51):
            assert app._should_run("ookla") is False

    def test_frequency_fallback_default(self, mock_config):
        """Sites undefined in the config fall back to 100 (always run)."""
        app = _make_app(mock_config)
        # site name not in the config
        assert app._should_run("unknown_site") is True

    def test_frequency_negative(self, mock_config):
        """A negative frequency also skips."""
        mock_config.set("frequency", "cloudflare", "-10")
        app = _make_app(mock_config)
        assert app._should_run("cloudflare") is False

    def test_frequency_over_100(self, mock_config):
        """A frequency over 100 still always runs."""
        mock_config.set("frequency", "cloudflare", "200")
        app = _make_app(mock_config)
        assert app._should_run("cloudflare") is True
