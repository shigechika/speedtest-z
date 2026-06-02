"""Tests for auto_consent (auto-approving consent via --yes)."""

import argparse
from unittest.mock import patch

from speedtest_z.runner import SpeedtestZ


def _make_app(mock_config, yes=False):
    """Create a SpeedtestZ instance, bypassing the WebDriver."""
    with patch.object(SpeedtestZ, "__init__", lambda self, *a, **kw: None):
        app = SpeedtestZ.__new__(SpeedtestZ)
        app.config = mock_config
        app.auto_consent = yes
    return app


class TestAutoConsent:
    """Tests for propagation of the auto_consent flag."""

    def test_default_false(self, mock_config):
        """auto_consent defaults to False."""
        app = _make_app(mock_config)
        assert app.auto_consent is False

    def test_yes_flag_sets_true(self, mock_config):
        """yes=True sets auto_consent=True."""
        app = _make_app(mock_config, yes=True)
        assert app.auto_consent is True

    def test_init_with_yes_arg(self, mock_config, sample_config_ini):
        """Passing args with --yes to SpeedtestZ.__init__ sets auto_consent=True."""
        args = argparse.Namespace(
            config=str(sample_config_ini),
            dry_run=True,
            headless=True,
            timeout=None,
            list_sites=False,
            debug=False,
            yes=True,
            sites=[],
        )
        with patch.object(SpeedtestZ, "_init_driver"), patch("speedtest_z.runner.signal.signal"):
            app = SpeedtestZ(args)
        assert app.auto_consent is True

    def test_init_without_yes_arg(self, mock_config, sample_config_ini):
        """Passing args without --yes to SpeedtestZ.__init__ sets auto_consent=False."""
        args = argparse.Namespace(
            config=str(sample_config_ini),
            dry_run=True,
            headless=True,
            timeout=None,
            list_sites=False,
            debug=False,
            yes=False,
            sites=[],
        )
        with patch.object(SpeedtestZ, "_init_driver"), patch("speedtest_z.runner.signal.signal"):
            app = SpeedtestZ(args)
        assert app.auto_consent is False

    def test_init_without_yes_attr(self, mock_config, sample_config_ini):
        """auto_consent=False even when args has no yes attribute (getattr fallback)."""
        args = argparse.Namespace(
            config=str(sample_config_ini),
            dry_run=True,
            headless=True,
            timeout=None,
            list_sites=False,
            debug=False,
            sites=[],
        )
        with patch.object(SpeedtestZ, "_init_driver"), patch("speedtest_z.runner.signal.signal"):
            app = SpeedtestZ(args)
        assert app.auto_consent is False
