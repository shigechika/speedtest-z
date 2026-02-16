"""auto_consent（--yes による同意自動承諾）のテスト"""

import argparse
from unittest.mock import patch, MagicMock

from speedtest_z.main import SpeedtestZ


def _make_app(mock_config, yes=False):
    """WebDriver を迂回して SpeedtestZ インスタンスを作成"""
    with patch.object(SpeedtestZ, "__init__", lambda self, *a, **kw: None):
        app = SpeedtestZ.__new__(SpeedtestZ)
        app.config = mock_config
        app.auto_consent = yes
    return app


class TestAutoConsent:
    """auto_consent フラグの伝播テスト"""

    def test_default_false(self, mock_config):
        """デフォルトで auto_consent=False"""
        app = _make_app(mock_config)
        assert app.auto_consent is False

    def test_yes_flag_sets_true(self, mock_config):
        """yes=True で auto_consent=True"""
        app = _make_app(mock_config, yes=True)
        assert app.auto_consent is True

    def test_init_with_yes_arg(self, mock_config, sample_config_ini):
        """SpeedtestZ.__init__ に --yes 付き args を渡すと auto_consent=True"""
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
        with patch.object(SpeedtestZ, "_init_driver"):
            with patch("speedtest_z.main.signal.signal"):
                app = SpeedtestZ(args)
        assert app.auto_consent is True

    def test_init_without_yes_arg(self, mock_config, sample_config_ini):
        """SpeedtestZ.__init__ に --yes なし args を渡すと auto_consent=False"""
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
        with patch.object(SpeedtestZ, "_init_driver"):
            with patch("speedtest_z.main.signal.signal"):
                app = SpeedtestZ(args)
        assert app.auto_consent is False

    def test_init_without_yes_attr(self, mock_config, sample_config_ini):
        """args に yes 属性がない場合でも auto_consent=False（getattr フォールバック）"""
        args = argparse.Namespace(
            config=str(sample_config_ini),
            dry_run=True,
            headless=True,
            timeout=None,
            list_sites=False,
            debug=False,
            sites=[],
        )
        with patch.object(SpeedtestZ, "_init_driver"):
            with patch("speedtest_z.main.signal.signal"):
                app = SpeedtestZ(args)
        assert app.auto_consent is False
