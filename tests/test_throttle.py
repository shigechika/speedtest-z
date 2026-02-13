"""スロットリング（_should_run）のテスト"""

from unittest.mock import patch, MagicMock

from speedtest_z.main import SpeedtestZ


def _make_app(mock_config, explicit_sites=False):
    """WebDriver を迂回して SpeedtestZ インスタンスを作成"""
    with patch.object(SpeedtestZ, "__init__", lambda self, *a, **kw: None):
        app = SpeedtestZ.__new__(SpeedtestZ)
        app.config = mock_config
        app.explicit_sites = explicit_sites
    return app


class TestShouldRun:
    """_should_run() のテスト"""

    def test_explicit_sites_always_true(self, mock_config):
        """CLI でサイト明示指定時は常に True"""
        app = _make_app(mock_config, explicit_sites=True)
        assert app._should_run("cloudflare") is True
        assert app._should_run("mlab") is True

    def test_frequency_100(self, mock_config):
        """frequency=100 は常に実行"""
        app = _make_app(mock_config)
        # cloudflare は config で 100
        assert app._should_run("cloudflare") is True

    def test_frequency_0(self, mock_config):
        """frequency=0 は常にスキップ"""
        mock_config.set("frequency", "cloudflare", "0")
        app = _make_app(mock_config)
        assert app._should_run("cloudflare") is False

    def test_frequency_50_run(self, mock_config):
        """frequency=50 で乱数が範囲内なら実行"""
        app = _make_app(mock_config)
        # ookla は config で 50
        with patch("speedtest_z.main.random.randint", return_value=30):
            assert app._should_run("ookla") is True

    def test_frequency_50_skip(self, mock_config):
        """frequency=50 で乱数が範囲外ならスキップ"""
        app = _make_app(mock_config)
        with patch("speedtest_z.main.random.randint", return_value=80):
            assert app._should_run("ookla") is False

    def test_frequency_boundary_run(self, mock_config):
        """frequency=50 で乱数がちょうど50なら実行"""
        app = _make_app(mock_config)
        with patch("speedtest_z.main.random.randint", return_value=50):
            assert app._should_run("ookla") is True

    def test_frequency_boundary_skip(self, mock_config):
        """frequency=50 で乱数が51ならスキップ"""
        app = _make_app(mock_config)
        with patch("speedtest_z.main.random.randint", return_value=51):
            assert app._should_run("ookla") is False

    def test_frequency_fallback_default(self, mock_config):
        """config に未定義のサイトはフォールバック 100（常に実行）"""
        app = _make_app(mock_config)
        # config にないサイト名
        assert app._should_run("unknown_site") is True

    def test_frequency_negative(self, mock_config):
        """frequency が負の値でもスキップ"""
        mock_config.set("frequency", "cloudflare", "-10")
        app = _make_app(mock_config)
        assert app._should_run("cloudflare") is False

    def test_frequency_over_100(self, mock_config):
        """frequency が 100 超でも常に実行"""
        mock_config.set("frequency", "cloudflare", "200")
        app = _make_app(mock_config)
        assert app._should_run("cloudflare") is True
