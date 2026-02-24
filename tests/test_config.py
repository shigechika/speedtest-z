"""設定ファイル探索のテスト"""

import os
from unittest.mock import patch

from speedtest_z.config import _find_config, _setup_logging
from speedtest_z.runner import SpeedtestZ


class TestFindConfig:
    """_find_config() のテスト"""

    def test_cli_path_exists(self, tmp_path):
        """CLI で指定したパスにファイルがあれば返す"""
        f = tmp_path / "my.ini"
        f.write_text("[general]\n")
        assert _find_config("config.ini", cli_path=str(f)) == str(f)

    def test_cli_path_not_exists(self, tmp_path):
        """CLI で指定したパスにファイルがなければ None"""
        result = _find_config("config.ini", cli_path=str(tmp_path / "no.ini"))
        assert result is None

    def test_current_dir(self, tmp_path, monkeypatch):
        """カレントディレクトリの config.ini を検出"""
        (tmp_path / "config.ini").write_text("[general]\n")
        monkeypatch.chdir(tmp_path)
        assert _find_config("config.ini") == "config.ini"

    def test_xdg_config_home(self, tmp_path, monkeypatch):
        """XDG_CONFIG_HOME 配下を検出"""
        xdg = tmp_path / "xdg"
        conf_dir = xdg / "speedtest-z"
        conf_dir.mkdir(parents=True)
        (conf_dir / "config.ini").write_text("[general]\n")

        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
        # カレントに config.ini がないディレクトリへ移動
        monkeypatch.chdir(tmp_path)
        assert _find_config("config.ini") == str(conf_dir / "config.ini")

    def test_xdg_default(self, tmp_path, monkeypatch):
        """XDG_CONFIG_HOME 未設定時は ~/.config を使う"""
        fake_home = tmp_path / "home"
        conf_dir = fake_home / ".config" / "speedtest-z"
        conf_dir.mkdir(parents=True)
        (conf_dir / "config.ini").write_text("[general]\n")

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(fake_home))
        monkeypatch.chdir(tmp_path)
        assert _find_config("config.ini") == str(conf_dir / "config.ini")

    def test_etc_fallback(self, tmp_path, monkeypatch):
        """/etc/speedtest-z/ にフォールバック"""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty"))
        etc_dir = tmp_path / "etc" / "speedtest-z"
        etc_dir.mkdir(parents=True)
        (etc_dir / "config.ini").write_text("[general]\n")
        # os.path.isfile を差し替えて /etc/speedtest-z/ をシミュレート
        _real_isfile = os.path.isfile

        def patched_isfile(path):
            if path == "/etc/speedtest-z/config.ini":
                return _real_isfile(str(etc_dir / "config.ini"))
            return _real_isfile(path)

        monkeypatch.setattr("speedtest_z.config.os.path.isfile", patched_isfile)
        assert _find_config("config.ini") == "/etc/speedtest-z/config.ini"

    def test_cwd_over_etc(self, tmp_path, monkeypatch):
        """CWD は /etc/speedtest-z/ より優先"""
        (tmp_path / "config.ini").write_text("[general]\n")
        monkeypatch.chdir(tmp_path)
        # /etc にもあっても CWD が優先される
        assert _find_config("config.ini") == "config.ini"

    def test_xdg_over_etc(self, tmp_path, monkeypatch):
        """XDG は /etc/speedtest-z/ より優先"""
        xdg = tmp_path / "xdg"
        conf_dir = xdg / "speedtest-z"
        conf_dir.mkdir(parents=True)
        (conf_dir / "config.ini").write_text("[general]\n")
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
        monkeypatch.chdir(tmp_path)
        assert _find_config("config.ini") == str(conf_dir / "config.ini")

    def test_not_found(self, tmp_path, monkeypatch):
        """どこにもなければ None"""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty"))
        assert _find_config("config.ini") is None

    def test_cli_path_takes_priority(self, tmp_path, monkeypatch):
        """CLI 指定はカレントディレクトリより優先"""
        (tmp_path / "config.ini").write_text("[cwd]\n")
        cli_file = tmp_path / "cli.ini"
        cli_file.write_text("[cli]\n")

        monkeypatch.chdir(tmp_path)
        assert _find_config("config.ini", cli_path=str(cli_file)) == str(cli_file)

    def test_logging_ini(self, tmp_path, monkeypatch):
        """logging.ini も同じ探索ロジックで見つかる"""
        (tmp_path / "logging.ini").write_text("[loggers]\n")
        monkeypatch.chdir(tmp_path)
        assert _find_config("logging.ini") == "logging.ini"


class TestSetupLogging:
    """_setup_logging() のテスト"""

    def test_no_logging_ini(self, tmp_path, monkeypatch):
        """logging.ini がなければ basicConfig で初期化"""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty"))
        with patch("speedtest_z.config.logging.basicConfig") as mock_basic:
            _setup_logging(debug=False)
            mock_basic.assert_called_once()

    def test_debug_mode(self, tmp_path, monkeypatch):
        """debug=True で DEBUG レベルに設定"""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty"))
        with patch("speedtest_z.config.logging.basicConfig") as mock_basic:
            _setup_logging(debug=True)
            call_kwargs = mock_basic.call_args
            assert call_kwargs[1]["level"] == 10  # logging.DEBUG


class TestChromeProfileDir:
    """chrome_profile_dir 設定のテスト"""

    def _make_app(self, mock_config):
        """WebDriver を迂回して SpeedtestZ インスタンスを作成"""
        with patch.object(SpeedtestZ, "__init__", lambda self, *a, **kw: None):
            app = SpeedtestZ.__new__(SpeedtestZ)
            app.config = mock_config
        return app

    def test_default_path(self, mock_config):
        """デフォルトで ~/.config/speedtest-z/chrome-profile が設定される"""
        app = self._make_app(mock_config)
        app.chrome_profile_dir = os.path.expanduser(
            app.config.get(
                "general", "chrome_profile_dir", fallback="~/.config/speedtest-z/chrome-profile"
            )
        )
        expected = os.path.expanduser("~/.config/speedtest-z/chrome-profile")
        assert app.chrome_profile_dir == expected

    def test_custom_path(self, mock_config):
        """config でカスタムパスを指定"""
        mock_config.set("general", "chrome_profile_dir", "/tmp/my-chrome-profile")
        app = self._make_app(mock_config)
        app.chrome_profile_dir = os.path.expanduser(
            app.config.get(
                "general", "chrome_profile_dir", fallback="~/.config/speedtest-z/chrome-profile"
            )
        )
        assert app.chrome_profile_dir == "/tmp/my-chrome-profile"

    def test_tilde_expansion(self, mock_config):
        """~ がホームディレクトリに展開される"""
        mock_config.set("general", "chrome_profile_dir", "~/my-profile")
        app = self._make_app(mock_config)
        app.chrome_profile_dir = os.path.expanduser(
            app.config.get(
                "general", "chrome_profile_dir", fallback="~/.config/speedtest-z/chrome-profile"
            )
        )
        assert "~" not in app.chrome_profile_dir
        assert app.chrome_profile_dir.endswith("my-profile")
