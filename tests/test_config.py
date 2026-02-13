"""設定ファイル探索のテスト"""

import os
from unittest.mock import patch

from speedtest_z.main import _find_config, _setup_logging


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
        with patch("speedtest_z.main.logging.basicConfig") as mock_basic:
            _setup_logging(debug=False)
            mock_basic.assert_called_once()

    def test_debug_mode(self, tmp_path, monkeypatch):
        """debug=True で DEBUG レベルに設定"""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty"))
        with patch("speedtest_z.main.logging.basicConfig") as mock_basic:
            _setup_logging(debug=True)
            call_kwargs = mock_basic.call_args
            assert call_kwargs[1]["level"] == 10  # logging.DEBUG
