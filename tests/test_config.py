"""Tests for config file discovery."""

import logging
import os
import sys
from unittest.mock import patch

from speedtest_z.config import (
    _find_config,
    _redirect_console_logging_to_stderr,
    _setup_logging,
)
from speedtest_z.runner import SpeedtestZ


class TestFindConfig:
    """Tests for _find_config()."""

    def test_cli_path_exists(self, tmp_path):
        """Return the CLI-specified path if the file exists."""
        f = tmp_path / "my.ini"
        f.write_text("[general]\n")
        assert _find_config("config.ini", cli_path=str(f)) == str(f)

    def test_cli_path_not_exists(self, tmp_path):
        """None if the CLI-specified path does not exist."""
        result = _find_config("config.ini", cli_path=str(tmp_path / "no.ini"))
        assert result is None

    def test_current_dir(self, tmp_path, monkeypatch):
        """Detect config.ini in the current directory."""
        (tmp_path / "config.ini").write_text("[general]\n")
        monkeypatch.chdir(tmp_path)
        assert _find_config("config.ini") == "config.ini"

    def test_xdg_config_home(self, tmp_path, monkeypatch):
        """Detect config under XDG_CONFIG_HOME."""
        xdg = tmp_path / "xdg"
        conf_dir = xdg / "speedtest-z"
        conf_dir.mkdir(parents=True)
        (conf_dir / "config.ini").write_text("[general]\n")

        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
        # Move to a directory that has no config.ini in CWD.
        monkeypatch.chdir(tmp_path)
        assert _find_config("config.ini") == str(conf_dir / "config.ini")

    def test_xdg_default(self, tmp_path, monkeypatch):
        """Use ~/.config when XDG_CONFIG_HOME is unset."""
        fake_home = tmp_path / "home"
        conf_dir = fake_home / ".config" / "speedtest-z"
        conf_dir.mkdir(parents=True)
        (conf_dir / "config.ini").write_text("[general]\n")

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(fake_home))
        monkeypatch.chdir(tmp_path)
        assert _find_config("config.ini") == str(conf_dir / "config.ini")

    def test_xdg_empty_string_falls_back_to_home(self, tmp_path, monkeypatch):
        """XDG_CONFIG_HOME='' (set but empty) falls back to ~/.config, not a relative path."""
        fake_home = tmp_path / "home"
        conf_dir = fake_home / ".config" / "speedtest-z"
        conf_dir.mkdir(parents=True)
        (conf_dir / "config.ini").write_text("[general]\n")

        monkeypatch.setenv("XDG_CONFIG_HOME", "")  # set but empty
        monkeypatch.setenv("HOME", str(fake_home))
        monkeypatch.chdir(tmp_path)
        assert _find_config("config.ini") == str(conf_dir / "config.ini")

    def test_etc_fallback(self, tmp_path, monkeypatch):
        """Fall back to /etc/speedtest-z/."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty"))
        etc_dir = tmp_path / "etc" / "speedtest-z"
        etc_dir.mkdir(parents=True)
        (etc_dir / "config.ini").write_text("[general]\n")
        # Patch os.path.isfile to simulate /etc/speedtest-z/.
        _real_isfile = os.path.isfile

        def patched_isfile(path):
            if path == "/etc/speedtest-z/config.ini":
                return _real_isfile(str(etc_dir / "config.ini"))
            return _real_isfile(path)

        monkeypatch.setattr("speedtest_z.config.os.path.isfile", patched_isfile)
        assert _find_config("config.ini") == "/etc/speedtest-z/config.ini"

    def test_cwd_over_etc(self, tmp_path, monkeypatch):
        """CWD takes priority over /etc/speedtest-z/."""
        (tmp_path / "config.ini").write_text("[general]\n")
        monkeypatch.chdir(tmp_path)
        # CWD wins even if /etc also has one.
        assert _find_config("config.ini") == "config.ini"

    def test_xdg_over_etc(self, tmp_path, monkeypatch):
        """XDG takes priority over /etc/speedtest-z/."""
        xdg = tmp_path / "xdg"
        conf_dir = xdg / "speedtest-z"
        conf_dir.mkdir(parents=True)
        (conf_dir / "config.ini").write_text("[general]\n")
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
        monkeypatch.chdir(tmp_path)
        assert _find_config("config.ini") == str(conf_dir / "config.ini")

    def test_not_found(self, tmp_path, monkeypatch):
        """None if not found anywhere."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty"))
        assert _find_config("config.ini") is None

    def test_cli_path_takes_priority(self, tmp_path, monkeypatch):
        """A CLI-specified path takes priority over the current directory."""
        (tmp_path / "config.ini").write_text("[cwd]\n")
        cli_file = tmp_path / "cli.ini"
        cli_file.write_text("[cli]\n")

        monkeypatch.chdir(tmp_path)
        assert _find_config("config.ini", cli_path=str(cli_file)) == str(cli_file)

    def test_logging_ini(self, tmp_path, monkeypatch):
        """logging.ini is found via the same discovery logic."""
        (tmp_path / "logging.ini").write_text("[loggers]\n")
        monkeypatch.chdir(tmp_path)
        assert _find_config("logging.ini") == "logging.ini"


class TestSetupLogging:
    """Tests for _setup_logging()."""

    def test_no_logging_ini(self, tmp_path, monkeypatch):
        """Initialize via basicConfig when there is no logging.ini."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty"))
        with patch("speedtest_z.config.logging.basicConfig") as mock_basic:
            _setup_logging(debug=False)
            mock_basic.assert_called_once()

    def test_debug_mode(self, tmp_path, monkeypatch):
        """debug=True sets the DEBUG level."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "empty"))
        with patch("speedtest_z.config.logging.basicConfig") as mock_basic:
            _setup_logging(debug=True)
            call_kwargs = mock_basic.call_args
            assert call_kwargs[1]["level"] == 10  # logging.DEBUG

    def test_redirect_console_logging_to_stderr(self):
        """A stdout StreamHandler is redirected to stderr; file handlers untouched."""
        root = logging.getLogger()
        saved = root.handlers[:]
        try:
            stdout_handler = logging.StreamHandler(sys.stdout)
            stderr_handler = logging.StreamHandler(sys.stderr)
            root.handlers = [stdout_handler, stderr_handler]
            _redirect_console_logging_to_stderr()
            assert stdout_handler.stream is sys.stderr
            assert stderr_handler.stream is sys.stderr  # already stderr, unchanged
        finally:
            root.handlers = saved

    def test_setup_logging_stderr_redirects_with_ini(self, tmp_path, monkeypatch):
        """With a logging.ini present, stream='stderr' triggers the redirect."""
        (tmp_path / "logging.ini").write_text("[loggers]\nkeys=root\n")
        monkeypatch.chdir(tmp_path)
        with (
            patch("speedtest_z.config.logging.config.fileConfig"),
            patch("speedtest_z.config._redirect_console_logging_to_stderr") as mock_redirect,
        ):
            _setup_logging(debug=False, stream="stderr")
            mock_redirect.assert_called_once()

    def test_setup_logging_stdout_no_redirect_with_ini(self, tmp_path, monkeypatch):
        """With a logging.ini present, the default stdout stream does not redirect."""
        (tmp_path / "logging.ini").write_text("[loggers]\nkeys=root\n")
        monkeypatch.chdir(tmp_path)
        with (
            patch("speedtest_z.config.logging.config.fileConfig"),
            patch("speedtest_z.config._redirect_console_logging_to_stderr") as mock_redirect,
        ):
            _setup_logging(debug=False, stream="stdout")
            mock_redirect.assert_not_called()


class TestChromeProfileDir:
    """Tests for the chrome_profile_dir setting."""

    def _make_app(self, mock_config):
        """Create a SpeedtestZ instance, bypassing the WebDriver."""
        with patch.object(SpeedtestZ, "__init__", lambda self, *a, **kw: None):
            app = SpeedtestZ.__new__(SpeedtestZ)
            app.config = mock_config
        return app

    def test_default_path(self, mock_config):
        """Defaults to ~/.config/speedtest-z/chrome-profile."""
        app = self._make_app(mock_config)
        app.chrome_profile_dir = os.path.expanduser(
            app.config.get(
                "general", "chrome_profile_dir", fallback="~/.config/speedtest-z/chrome-profile"
            )
        )
        expected = os.path.expanduser("~/.config/speedtest-z/chrome-profile")
        assert app.chrome_profile_dir == expected

    def test_custom_path(self, mock_config):
        """Specify a custom path via config."""
        mock_config.set("general", "chrome_profile_dir", "/tmp/my-chrome-profile")
        app = self._make_app(mock_config)
        app.chrome_profile_dir = os.path.expanduser(
            app.config.get(
                "general", "chrome_profile_dir", fallback="~/.config/speedtest-z/chrome-profile"
            )
        )
        assert app.chrome_profile_dir == "/tmp/my-chrome-profile"

    def test_tilde_expansion(self, mock_config):
        """~ is expanded to the home directory."""
        mock_config.set("general", "chrome_profile_dir", "~/my-profile")
        app = self._make_app(mock_config)
        app.chrome_profile_dir = os.path.expanduser(
            app.config.get(
                "general", "chrome_profile_dir", fallback="~/.config/speedtest-z/chrome-profile"
            )
        )
        assert "~" not in app.chrome_profile_dir
        assert app.chrome_profile_dir.endswith("my-profile")
