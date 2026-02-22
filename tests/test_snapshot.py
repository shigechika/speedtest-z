"""take_snapshot のテスト"""

from unittest.mock import MagicMock, patch

from speedtest_z.runner import SpeedtestZ


def _make_app(snapshot_enable=False, snapshot_dir="/tmp/snapshots"):
    """WebDriver を迂回して SpeedtestZ インスタンスを作成"""
    with patch.object(SpeedtestZ, "__init__", lambda self, *a, **kw: None):
        app = SpeedtestZ.__new__(SpeedtestZ)
        app.snapshot_enable = snapshot_enable
        app.snapshot_dir = snapshot_dir
        app.driver = MagicMock()
    return app


class TestTakeSnapshot:
    """take_snapshot() のテスト"""

    def test_disabled_does_nothing(self):
        """snapshot_enable=False の場合は何もしない"""
        app = _make_app(snapshot_enable=False)
        app.take_snapshot("test")
        app.driver.save_screenshot.assert_not_called()

    def test_enabled_saves_screenshot(self):
        """snapshot_enable=True の場合スクリーンショットを保存"""
        app = _make_app(snapshot_enable=True, snapshot_dir="/tmp/snaps")
        app.take_snapshot("cloudflare")
        app.driver.save_screenshot.assert_called_once_with("/tmp/snaps/cloudflare.png")

    def test_exception_handled(self):
        """save_screenshot が失敗してもエラーにならない"""
        app = _make_app(snapshot_enable=True)
        app.driver.save_screenshot.side_effect = Exception("write error")
        # 例外が伝播しないことを確認
        app.take_snapshot("test")
