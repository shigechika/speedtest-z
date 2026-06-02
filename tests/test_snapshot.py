"""Tests for take_snapshot."""

from unittest.mock import MagicMock, patch

from speedtest_z.runner import SpeedtestZ


def _make_app(snapshot_enable=False, snapshot_dir="/tmp/snapshots"):
    """Create a SpeedtestZ instance, bypassing the WebDriver."""
    with patch.object(SpeedtestZ, "__init__", lambda self, *a, **kw: None):
        app = SpeedtestZ.__new__(SpeedtestZ)
        app.snapshot_enable = snapshot_enable
        app.snapshot_dir = snapshot_dir
        app.driver = MagicMock()
    return app


class TestTakeSnapshot:
    """Tests for take_snapshot()."""

    def test_disabled_does_nothing(self):
        """Do nothing when snapshot_enable=False."""
        app = _make_app(snapshot_enable=False)
        app.take_snapshot("test")
        app.driver.save_screenshot.assert_not_called()

    def test_enabled_saves_screenshot(self):
        """Save a screenshot when snapshot_enable=True."""
        app = _make_app(snapshot_enable=True, snapshot_dir="/tmp/snaps")
        app.take_snapshot("cloudflare")
        app.driver.save_screenshot.assert_called_once_with("/tmp/snaps/cloudflare.png")

    def test_exception_handled(self):
        """No error is raised even when save_screenshot fails."""
        app = _make_app(snapshot_enable=True)
        app.driver.save_screenshot.side_effect = Exception("write error")
        # Verify the exception does not propagate
        app.take_snapshot("test")
