"""Tests for the CLI parser."""

from unittest.mock import MagicMock, patch

import pytest

from speedtest_z.cli import (
    _build_parser,
    _show_manual,
    main,
)
from speedtest_z.i18n import _msg
from speedtest_z.sites import AVAILABLE_SITES


class TestBuildParser:
    """Tests for _build_parser()."""

    def test_default_args(self):
        """Check the default arguments."""
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.config is None
        assert args.dry_run is False
        assert args.headless is None
        assert args.timeout is None
        assert args.list_sites is False
        assert args.debug is False
        assert args.yes is False
        assert args.sites == []

    def test_dry_run(self):
        """-n sets dry_run=True."""
        parser = _build_parser()
        args = parser.parse_args(["-n"])
        assert args.dry_run is True

    def test_dry_run_long(self):
        """--dry-run behaves the same."""
        parser = _build_parser()
        args = parser.parse_args(["--dry-run"])
        assert args.dry_run is True

    def test_headless(self):
        """--headless sets headless=True."""
        parser = _build_parser()
        args = parser.parse_args(["--headless"])
        assert args.headless is True

    def test_no_headless(self):
        """--no-headless sets headless=False."""
        parser = _build_parser()
        args = parser.parse_args(["--no-headless"])
        assert args.headless is False

    def test_headed_alias(self):
        """--headed is an alias for --no-headless."""
        parser = _build_parser()
        args = parser.parse_args(["--headed"])
        assert args.headless is False

    def test_timeout(self):
        """--timeout sets the timeout."""
        parser = _build_parser()
        args = parser.parse_args(["--timeout", "60"])
        assert args.timeout == 60

    def test_config_path(self):
        """-c specifies the config file path."""
        parser = _build_parser()
        args = parser.parse_args(["-c", "/tmp/my.ini"])
        assert args.config == "/tmp/my.ini"

    def test_debug(self):
        """-d enables debug mode."""
        parser = _build_parser()
        args = parser.parse_args(["-d"])
        assert args.debug is True

    def test_single_site(self):
        """Specify a single site name."""
        parser = _build_parser()
        args = parser.parse_args(["cloudflare"])
        assert args.sites == ["cloudflare"]

    def test_multiple_sites(self):
        """Specify multiple site names."""
        parser = _build_parser()
        args = parser.parse_args(["cloudflare", "netflix"])
        assert args.sites == ["cloudflare", "netflix"]

    def test_list_sites_flag(self):
        """--list-sites flag."""
        parser = _build_parser()
        args = parser.parse_args(["--list-sites"])
        assert args.list_sites is True

    def test_epilog_contains_github_url(self):
        """The epilog should contain the GitHub URL."""
        parser = _build_parser()
        assert "https://github.com/shigechika/speedtest-z" in parser.epilog

    def test_man_flag(self):
        """-m sets man=True."""
        parser = _build_parser()
        args = parser.parse_args(["-m"])
        assert args.man is True

    def test_man_long_flag(self):
        """--man behaves the same."""
        parser = _build_parser()
        args = parser.parse_args(["--man"])
        assert args.man is True

    def test_man_default_false(self):
        """man defaults to False."""
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.man is False

    def test_yes_short(self):
        """-y sets yes=True."""
        parser = _build_parser()
        args = parser.parse_args(["-y"])
        assert args.yes is True

    def test_yes_long(self):
        """--yes behaves the same."""
        parser = _build_parser()
        args = parser.parse_args(["--yes"])
        assert args.yes is True


class TestShowManual:
    """Tests for _show_manual()."""

    def test_manual_text_contains_speedtest(self):
        """The manual text should contain speedtest-z."""
        with patch("pydoc.pager") as mock_pager:
            _show_manual()
            text = mock_pager.call_args[0][0]
            assert "speedtest-z" in text

    def test_manual_japanese_locale(self):
        """README.ja.md is shown in a Japanese locale."""
        with patch("pydoc.pager") as mock_pager, patch("speedtest_z.cli._LANG_JA", True):
            _show_manual()
            text = mock_pager.call_args[0][0]
            assert "特徴" in text

    def test_manual_english_locale(self):
        """README.md is shown in an English locale."""
        with patch("pydoc.pager") as mock_pager, patch("speedtest_z.cli._LANG_JA", False):
            _show_manual()
            text = mock_pager.call_args[0][0]
            assert "Features" in text


class TestMainMan:
    """Tests for the --man branch of main()."""

    def test_man_calls_show_manual(self):
        """--man should call _show_manual()."""
        with (
            patch("speedtest_z.cli._build_parser") as mock_parser,
            patch("speedtest_z.cli._show_manual") as mock_show,
        ):
            mock_args = MagicMock()
            mock_args.man = True
            mock_args.list_sites = False
            mock_parser.return_value.parse_args.return_value = mock_args
            main()
            mock_show.assert_called_once()


class TestMainListSites:
    """Tests for the --list-sites branch of main()."""

    def test_list_sites_output(self, capsys):
        """--list-sites prints the site list and exits."""
        with patch("speedtest_z.cli._build_parser") as mock_parser:
            mock_args = MagicMock()
            mock_args.man = False
            mock_args.list_sites = True
            mock_parser.return_value.parse_args.return_value = mock_args
            main()

        captured = capsys.readouterr()
        assert "Available test sites:" in captured.out
        for site in AVAILABLE_SITES:
            assert site in captured.out


class TestMainConfigRequired:
    """Tests that main() requires config.ini."""

    def test_exit_when_config_not_found(self):
        """sys.exit(1) when config.ini is not found."""
        with (
            patch("speedtest_z.cli._build_parser") as mock_parser,
            patch("speedtest_z.cli._setup_logging"),
            patch("speedtest_z.cli._find_config", return_value=None),
        ):
            mock_args = MagicMock()
            mock_args.man = False
            mock_args.list_sites = False
            mock_args.check = False
            mock_args.debug = False
            mock_args.config = None
            mock_parser.return_value.parse_args.return_value = mock_args
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_config_path_passed_to_speedtestz(self):
        """The discovered config path is set on args.config."""
        with (
            patch("speedtest_z.cli._build_parser") as mock_parser,
            patch("speedtest_z.cli._setup_logging"),
            patch("speedtest_z.cli._find_config", return_value="/found/config.ini"),
            patch("speedtest_z.runner.SpeedtestZ") as mock_stz,
            patch("speedtest_z.cli.get_site_runners", return_value={}),
            patch("sys.stdin") as mock_stdin,
        ):
            mock_args = MagicMock()
            mock_args.man = False
            mock_args.list_sites = False
            mock_args.check = False
            mock_args.debug = False
            mock_args.config = None
            mock_args.yes = True
            mock_args.sites = []
            mock_parser.return_value.parse_args.return_value = mock_args
            # Also mock the SpeedtestZ instance.
            mock_app = MagicMock()
            mock_stz.return_value = mock_app
            mock_stdin.isatty.return_value = False
            main()
            assert mock_args.config == "/found/config.ini"
            mock_stz.assert_called_once_with(mock_args)


class TestMainConfirmPrompt:
    """Tests for the confirmation prompt in main()."""

    def _make_args(self, yes=False, sites=None):
        """Build mock args for tests."""
        mock_args = MagicMock()
        mock_args.man = False
        mock_args.list_sites = False
        mock_args.check = False
        mock_args.debug = False
        mock_args.config = None
        mock_args.yes = yes
        mock_args.sites = sites or []
        return mock_args

    def test_prompt_shown_on_tty(self, capsys):
        """The confirmation prompt is shown on a TTY without --yes."""
        with (
            patch("speedtest_z.cli._build_parser") as mock_parser,
            patch("speedtest_z.cli._setup_logging"),
            patch("speedtest_z.cli._find_config", return_value="/tmp/config.ini"),
            patch("sys.stdin") as mock_stdin,
            patch("builtins.input", return_value="n"),
        ):
            mock_args = self._make_args()
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_stdin.isatty.return_value = True
            main()
        captured = capsys.readouterr()
        # Locale-independent assertion.
        assert _msg("confirm_abort") in captured.out

    def test_prompt_yes_continues(self):
        """Entering y at the confirmation prompt continues."""
        with (
            patch("speedtest_z.cli._build_parser") as mock_parser,
            patch("speedtest_z.cli._setup_logging"),
            patch("speedtest_z.cli._find_config", return_value="/tmp/config.ini"),
            patch("speedtest_z.runner.SpeedtestZ") as mock_stz,
            patch("speedtest_z.cli.get_site_runners", return_value={}),
            patch("sys.stdin") as mock_stdin,
            patch("builtins.input", return_value="y"),
        ):
            mock_args = self._make_args()
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_stdin.isatty.return_value = True
            mock_app = MagicMock()
            mock_stz.return_value = mock_app
            main()
            mock_stz.assert_called_once()

    def test_prompt_shown_with_yes_flag(self):
        """The confirmation prompt is still shown on a TTY even with --yes."""
        with (
            patch("speedtest_z.cli._build_parser") as mock_parser,
            patch("speedtest_z.cli._setup_logging"),
            patch("speedtest_z.cli._find_config", return_value="/tmp/config.ini"),
            patch("speedtest_z.runner.SpeedtestZ") as mock_stz,
            patch("speedtest_z.cli.get_site_runners", return_value={}),
            patch("sys.stdin") as mock_stdin,
            patch("builtins.input", return_value="y") as mock_input,
        ):
            mock_args = self._make_args(yes=True)
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_stdin.isatty.return_value = True
            mock_app = MagicMock()
            mock_stz.return_value = mock_app
            main()
            mock_input.assert_called_once()
            mock_stz.assert_called_once()

    def test_prompt_skipped_on_non_tty(self):
        """The prompt is not shown on a non-TTY (pipe/cron)."""
        with (
            patch("speedtest_z.cli._build_parser") as mock_parser,
            patch("speedtest_z.cli._setup_logging"),
            patch("speedtest_z.cli._find_config", return_value="/tmp/config.ini"),
            patch("speedtest_z.runner.SpeedtestZ") as mock_stz,
            patch("speedtest_z.cli.get_site_runners", return_value={}),
            patch("sys.stdin") as mock_stdin,
            patch("builtins.input") as mock_input,
        ):
            mock_args = self._make_args()
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_stdin.isatty.return_value = False
            mock_app = MagicMock()
            mock_stz.return_value = mock_app
            main()
            mock_input.assert_not_called()
            mock_stz.assert_called_once()

    def test_prompt_shows_specified_sites(self, capsys):
        """When sites are specified, they appear in the prompt."""
        with (
            patch("speedtest_z.cli._build_parser") as mock_parser,
            patch("speedtest_z.cli._setup_logging"),
            patch("speedtest_z.cli._find_config", return_value="/tmp/config.ini"),
            patch("sys.stdin") as mock_stdin,
            patch("builtins.input", return_value="n"),
        ):
            mock_args = self._make_args(sites=["cloudflare", "netflix"])
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_stdin.isatty.return_value = True
            main()
        captured = capsys.readouterr()
        assert "cloudflare, netflix" in captured.out

    def test_prompt_abort_with_empty_input(self, capsys):
        """Empty input (just Enter) aborts."""
        with (
            patch("speedtest_z.cli._build_parser") as mock_parser,
            patch("speedtest_z.cli._setup_logging"),
            patch("speedtest_z.cli._find_config", return_value="/tmp/config.ini"),
            patch("speedtest_z.runner.SpeedtestZ") as mock_stz,
            patch("speedtest_z.cli.get_site_runners", return_value={}),
            patch("sys.stdin") as mock_stdin,
            patch("builtins.input", return_value=""),
        ):
            mock_args = self._make_args()
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_stdin.isatty.return_value = True
            main()
        captured = capsys.readouterr()
        assert _msg("confirm_abort") in captured.out
        mock_stz.assert_not_called()


class TestMainFatalExit:
    """main() exits non-zero when a site runner raises a fatal error."""

    def test_fatal_exception_exits_1(self):
        """A runner exception is logged and main() exits with code 1."""

        def _boom(app):
            raise RuntimeError("boom")

        with (
            patch("speedtest_z.cli._build_parser") as mock_parser,
            patch("speedtest_z.cli._setup_logging"),
            patch("speedtest_z.cli._find_config", return_value="/tmp/config.ini"),
            patch("speedtest_z.runner.SpeedtestZ") as mock_stz,
            patch("speedtest_z.cli.get_site_runners", return_value={"cloudflare": _boom}),
            patch("sys.stdin") as mock_stdin,
        ):
            mock_args = MagicMock()
            mock_args.man = False
            mock_args.list_sites = False
            mock_args.check = False
            mock_args.debug = False
            mock_args.config = None
            mock_args.output = "zabbix"
            mock_args.yes = True
            mock_args.sites = ["cloudflare"]
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_app = MagicMock()
            mock_stz.return_value = mock_app
            mock_stdin.isatty.return_value = False

            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
            mock_app.close.assert_called()  # finally still cleans up


class TestMainKeyboardInterrupt:
    """main() exits with 130 (128+SIGINT) when interrupted by Ctrl-C."""

    def test_keyboard_interrupt_exits_130(self):
        """A KeyboardInterrupt closes the app and exits with code 130."""

        def _interrupt(app):
            raise KeyboardInterrupt

        with (
            patch("speedtest_z.cli._build_parser") as mock_parser,
            patch("speedtest_z.cli._setup_logging"),
            patch("speedtest_z.cli._find_config", return_value="/tmp/config.ini"),
            patch("speedtest_z.runner.SpeedtestZ") as mock_stz,
            patch("speedtest_z.cli.get_site_runners", return_value={"cloudflare": _interrupt}),
            patch("sys.stdin") as mock_stdin,
        ):
            mock_args = MagicMock()
            mock_args.man = False
            mock_args.list_sites = False
            mock_args.check = False
            mock_args.debug = False
            mock_args.config = None
            mock_args.output = "zabbix"
            mock_args.yes = True
            mock_args.sites = ["cloudflare"]
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_app = MagicMock()
            mock_stz.return_value = mock_app
            mock_stdin.isatty.return_value = False

            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 130
            mock_app.close.assert_called()  # finally still cleans up


class TestI18nMessages:
    """Tests for _msg() switching between Japanese and English."""

    def test_msg_japanese(self):
        """_LANG_JA=True returns Japanese messages."""
        with patch("speedtest_z.i18n._LANG_JA", True):
            assert _msg("confirm_abort") == "中止しました。"
            assert _msg("manual_not_found") == "マニュアルが見つかりません。"

    def test_msg_english(self):
        """_LANG_JA=False returns English messages."""
        with patch("speedtest_z.i18n._LANG_JA", False):
            assert _msg("confirm_abort") == "Aborted."
            assert _msg("manual_not_found") == "Manual not found."

    def test_msg_with_kwargs_japanese(self):
        """Format arguments are expanded in a Japanese message."""
        with patch("speedtest_z.i18n._LANG_JA", True):
            result = _msg("config_not_found_cli", path="/tmp/test.ini")
            assert result == "/tmp/test.ini が見つかりません"

    def test_msg_with_kwargs_english(self):
        """Format arguments are expanded in an English message."""
        with patch("speedtest_z.i18n._LANG_JA", False):
            result = _msg("config_not_found_cli", path="/tmp/test.ini")
            assert result == "/tmp/test.ini not found"

    def test_confirm_prompt_japanese(self):
        """The Japanese confirmation prompt message."""
        with patch("speedtest_z.i18n._LANG_JA", True):
            result = _msg("confirm_prompt", count=2, sites="cloudflare, netflix")
            assert "2 サイトに接続します" in result
            assert "cloudflare, netflix" in result

    def test_confirm_prompt_english(self):
        """The English confirmation prompt message."""
        with patch("speedtest_z.i18n._LANG_JA", False):
            result = _msg("confirm_prompt", count=2, sites="cloudflare, netflix")
            assert "connecting to 2 site(s)" in result
            assert "cloudflare, netflix" in result

    def test_prompt_shown_japanese(self, capsys):
        """The Japanese prompt is shown in a Japanese locale."""
        with (
            patch("speedtest_z.cli._build_parser") as mock_parser,
            patch("speedtest_z.cli._setup_logging"),
            patch("speedtest_z.cli._find_config", return_value="/tmp/config.ini"),
            patch("sys.stdin") as mock_stdin,
            patch("builtins.input", return_value="n"),
            patch("speedtest_z.i18n._LANG_JA", True),
        ):
            mock_args = MagicMock()
            mock_args.man = False
            mock_args.list_sites = False
            mock_args.check = False
            mock_args.debug = False
            mock_args.config = None
            mock_args.yes = False
            mock_args.sites = ["cloudflare"]
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_stdin.isatty.return_value = True
            main()
        captured = capsys.readouterr()
        assert "サイトに接続します" in captured.out
        assert "中止しました。" in captured.out

    def test_prompt_shown_english(self, capsys):
        """The English prompt is shown in an English locale."""
        with (
            patch("speedtest_z.cli._build_parser") as mock_parser,
            patch("speedtest_z.cli._setup_logging"),
            patch("speedtest_z.cli._find_config", return_value="/tmp/config.ini"),
            patch("sys.stdin") as mock_stdin,
            patch("builtins.input", return_value="n"),
            patch("speedtest_z.i18n._LANG_JA", False),
        ):
            mock_args = MagicMock()
            mock_args.man = False
            mock_args.list_sites = False
            mock_args.check = False
            mock_args.debug = False
            mock_args.config = None
            mock_args.yes = False
            mock_args.sites = ["cloudflare"]
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_stdin.isatty.return_value = True
            main()
        captured = capsys.readouterr()
        assert "connecting to 1 site(s)" in captured.out
        assert "Aborted." in captured.out
