"""CLI パーサーのテスト"""

import pytest
from unittest.mock import patch, MagicMock

from speedtest_z.main import (
    _build_parser, _show_manual, _msg, main, AVAILABLE_SITES,
)


class TestBuildParser:
    """_build_parser() のテスト"""

    def test_default_args(self):
        """デフォルト引数の確認"""
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
        """-n で dry_run=True"""
        parser = _build_parser()
        args = parser.parse_args(["-n"])
        assert args.dry_run is True

    def test_dry_run_long(self):
        """--dry-run でも同様"""
        parser = _build_parser()
        args = parser.parse_args(["--dry-run"])
        assert args.dry_run is True

    def test_headless(self):
        """--headless で headless=True"""
        parser = _build_parser()
        args = parser.parse_args(["--headless"])
        assert args.headless is True

    def test_no_headless(self):
        """--no-headless で headless=False"""
        parser = _build_parser()
        args = parser.parse_args(["--no-headless"])
        assert args.headless is False

    def test_headed_alias(self):
        """--headed は --no-headless のエイリアス"""
        parser = _build_parser()
        args = parser.parse_args(["--headed"])
        assert args.headless is False

    def test_timeout(self):
        """--timeout でタイムアウト設定"""
        parser = _build_parser()
        args = parser.parse_args(["--timeout", "60"])
        assert args.timeout == 60

    def test_config_path(self):
        """-c で設定ファイルパス指定"""
        parser = _build_parser()
        args = parser.parse_args(["-c", "/tmp/my.ini"])
        assert args.config == "/tmp/my.ini"

    def test_debug(self):
        """-d でデバッグモード"""
        parser = _build_parser()
        args = parser.parse_args(["-d"])
        assert args.debug is True

    def test_single_site(self):
        """サイト名を1つ指定"""
        parser = _build_parser()
        args = parser.parse_args(["cloudflare"])
        assert args.sites == ["cloudflare"]

    def test_multiple_sites(self):
        """サイト名を複数指定"""
        parser = _build_parser()
        args = parser.parse_args(["cloudflare", "netflix"])
        assert args.sites == ["cloudflare", "netflix"]

    def test_list_sites_flag(self):
        """--list-sites フラグ"""
        parser = _build_parser()
        args = parser.parse_args(["--list-sites"])
        assert args.list_sites is True

    def test_man_flag(self):
        """-m で man=True"""
        parser = _build_parser()
        args = parser.parse_args(["-m"])
        assert args.man is True

    def test_man_long_flag(self):
        """--man でも同様"""
        parser = _build_parser()
        args = parser.parse_args(["--man"])
        assert args.man is True

    def test_man_default_false(self):
        """デフォルトで man=False"""
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.man is False

    def test_yes_short(self):
        """-y で yes=True"""
        parser = _build_parser()
        args = parser.parse_args(["-y"])
        assert args.yes is True

    def test_yes_long(self):
        """--yes でも同様"""
        parser = _build_parser()
        args = parser.parse_args(["--yes"])
        assert args.yes is True


class TestShowManual:
    """_show_manual() のテスト"""

    def test_manual_text_contains_speedtest(self):
        """マニュアルテキストに speedtest-z が含まれること"""
        with patch("pydoc.pager") as mock_pager:
            _show_manual()
            text = mock_pager.call_args[0][0]
            assert "speedtest-z" in text

    def test_manual_japanese_locale(self):
        """日本語ロケールで README.ja.md が表示されること"""
        with patch("pydoc.pager") as mock_pager, \
             patch("speedtest_z.main._LANG_JA", True):
            _show_manual()
            text = mock_pager.call_args[0][0]
            assert "特徴" in text

    def test_manual_english_locale(self):
        """英語ロケールで README.md が表示されること"""
        with patch("pydoc.pager") as mock_pager, \
             patch("speedtest_z.main._LANG_JA", False):
            _show_manual()
            text = mock_pager.call_args[0][0]
            assert "Features" in text


class TestMainMan:
    """main() の --man 分岐テスト"""

    def test_man_calls_show_manual(self):
        """--man で _show_manual() が呼ばれること"""
        with patch("speedtest_z.main._build_parser") as mock_parser, \
             patch("speedtest_z.main._show_manual") as mock_show:
            mock_args = MagicMock()
            mock_args.man = True
            mock_args.list_sites = False
            mock_parser.return_value.parse_args.return_value = mock_args
            main()
            mock_show.assert_called_once()


class TestMainListSites:
    """main() の --list-sites 分岐テスト"""

    def test_list_sites_output(self, capsys):
        """--list-sites でサイト一覧を出力して終了"""
        with patch("speedtest_z.main._build_parser") as mock_parser:
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
    """main() の config.ini 必須チェックテスト"""

    def test_exit_when_config_not_found(self):
        """config.ini が見つからない場合 sys.exit(1)"""
        with patch("speedtest_z.main._build_parser") as mock_parser, \
             patch("speedtest_z.main._setup_logging"), \
             patch("speedtest_z.main._find_config", return_value=None):
            mock_args = MagicMock()
            mock_args.man = False
            mock_args.list_sites = False
            mock_args.debug = False
            mock_args.config = None
            mock_parser.return_value.parse_args.return_value = mock_args
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_config_path_passed_to_speedtestz(self):
        """見つかった config パスが args.config に設定されること"""
        with patch("speedtest_z.main._build_parser") as mock_parser, \
             patch("speedtest_z.main._setup_logging"), \
             patch("speedtest_z.main._find_config", return_value="/found/config.ini"), \
             patch("speedtest_z.main.SpeedtestZ") as mock_stz, \
             patch("sys.stdin") as mock_stdin:
            mock_args = MagicMock()
            mock_args.man = False
            mock_args.list_sites = False
            mock_args.debug = False
            mock_args.config = None
            mock_args.yes = True
            mock_args.sites = []
            mock_parser.return_value.parse_args.return_value = mock_args
            # SpeedtestZ のインスタンスもモック
            mock_app = MagicMock()
            mock_stz.return_value = mock_app
            mock_stdin.isatty.return_value = False
            main()
            assert mock_args.config == "/found/config.ini"
            mock_stz.assert_called_once_with(mock_args)


class TestMainConfirmPrompt:
    """main() の確認プロンプトテスト"""

    def _make_args(self, yes=False, sites=None):
        """テスト用の mock args を生成"""
        mock_args = MagicMock()
        mock_args.man = False
        mock_args.list_sites = False
        mock_args.debug = False
        mock_args.config = None
        mock_args.yes = yes
        mock_args.sites = sites or []
        return mock_args

    def test_prompt_shown_on_tty(self, capsys):
        """TTY で --yes なしの場合、確認プロンプトが表示されること"""
        with patch("speedtest_z.main._build_parser") as mock_parser, \
             patch("speedtest_z.main._setup_logging"), \
             patch("speedtest_z.main._find_config", return_value="/tmp/config.ini"), \
             patch("sys.stdin") as mock_stdin, \
             patch("builtins.input", return_value="n"):
            mock_args = self._make_args()
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_stdin.isatty.return_value = True
            main()
        captured = capsys.readouterr()
        # ロケールに依存しないアサーション
        assert _msg("confirm_abort") in captured.out

    def test_prompt_yes_continues(self):
        """確認プロンプトで y を入力すると続行されること"""
        with patch("speedtest_z.main._build_parser") as mock_parser, \
             patch("speedtest_z.main._setup_logging"), \
             patch("speedtest_z.main._find_config", return_value="/tmp/config.ini"), \
             patch("speedtest_z.main.SpeedtestZ") as mock_stz, \
             patch("sys.stdin") as mock_stdin, \
             patch("builtins.input", return_value="y"):
            mock_args = self._make_args()
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_stdin.isatty.return_value = True
            mock_app = MagicMock()
            mock_stz.return_value = mock_app
            main()
            mock_stz.assert_called_once()

    def test_prompt_skipped_with_yes_flag(self):
        """--yes フラグで確認プロンプトがスキップされること"""
        with patch("speedtest_z.main._build_parser") as mock_parser, \
             patch("speedtest_z.main._setup_logging"), \
             patch("speedtest_z.main._find_config", return_value="/tmp/config.ini"), \
             patch("speedtest_z.main.SpeedtestZ") as mock_stz, \
             patch("sys.stdin") as mock_stdin, \
             patch("builtins.input") as mock_input:
            mock_args = self._make_args(yes=True)
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_stdin.isatty.return_value = True
            mock_app = MagicMock()
            mock_stz.return_value = mock_app
            main()
            mock_input.assert_not_called()
            mock_stz.assert_called_once()

    def test_prompt_skipped_on_non_tty(self):
        """非 TTY（パイプ/cron）ではプロンプトが表示されないこと"""
        with patch("speedtest_z.main._build_parser") as mock_parser, \
             patch("speedtest_z.main._setup_logging"), \
             patch("speedtest_z.main._find_config", return_value="/tmp/config.ini"), \
             patch("speedtest_z.main.SpeedtestZ") as mock_stz, \
             patch("sys.stdin") as mock_stdin, \
             patch("builtins.input") as mock_input:
            mock_args = self._make_args()
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_stdin.isatty.return_value = False
            mock_app = MagicMock()
            mock_stz.return_value = mock_app
            main()
            mock_input.assert_not_called()
            mock_stz.assert_called_once()

    def test_prompt_shows_specified_sites(self, capsys):
        """サイト指定時、指定サイトがプロンプトに表示されること"""
        with patch("speedtest_z.main._build_parser") as mock_parser, \
             patch("speedtest_z.main._setup_logging"), \
             patch("speedtest_z.main._find_config", return_value="/tmp/config.ini"), \
             patch("sys.stdin") as mock_stdin, \
             patch("builtins.input", return_value="n"):
            mock_args = self._make_args(sites=["cloudflare", "netflix"])
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_stdin.isatty.return_value = True
            main()
        captured = capsys.readouterr()
        assert "cloudflare, netflix" in captured.out

    def test_prompt_abort_with_empty_input(self, capsys):
        """空入力（Enter のみ）で中止されること"""
        with patch("speedtest_z.main._build_parser") as mock_parser, \
             patch("speedtest_z.main._setup_logging"), \
             patch("speedtest_z.main._find_config", return_value="/tmp/config.ini"), \
             patch("speedtest_z.main.SpeedtestZ") as mock_stz, \
             patch("sys.stdin") as mock_stdin, \
             patch("builtins.input", return_value=""):
            mock_args = self._make_args()
            mock_parser.return_value.parse_args.return_value = mock_args
            mock_stdin.isatty.return_value = True
            main()
        captured = capsys.readouterr()
        assert _msg("confirm_abort") in captured.out
        mock_stz.assert_not_called()


class TestI18nMessages:
    """_msg() の日英切り替えテスト"""

    def test_msg_japanese(self):
        """_LANG_JA=True で日本語メッセージが返ること"""
        with patch("speedtest_z.main._LANG_JA", True):
            assert _msg("confirm_abort") == "中止しました。"
            assert _msg("manual_not_found") == "マニュアルが見つかりません。"

    def test_msg_english(self):
        """_LANG_JA=False で英語メッセージが返ること"""
        with patch("speedtest_z.main._LANG_JA", False):
            assert _msg("confirm_abort") == "Aborted."
            assert _msg("manual_not_found") == "Manual not found."

    def test_msg_with_kwargs_japanese(self):
        """日本語メッセージのフォーマット引数が展開されること"""
        with patch("speedtest_z.main._LANG_JA", True):
            result = _msg("config_not_found_cli", path="/tmp/test.ini")
            assert "/tmp/test.ini が見つかりません" == result

    def test_msg_with_kwargs_english(self):
        """英語メッセージのフォーマット引数が展開されること"""
        with patch("speedtest_z.main._LANG_JA", False):
            result = _msg("config_not_found_cli", path="/tmp/test.ini")
            assert "/tmp/test.ini not found" == result

    def test_confirm_prompt_japanese(self):
        """日本語の確認プロンプトメッセージ"""
        with patch("speedtest_z.main._LANG_JA", True):
            result = _msg("confirm_prompt", count=2, sites="cloudflare, netflix")
            assert "2 サイトに接続します" in result
            assert "cloudflare, netflix" in result

    def test_confirm_prompt_english(self):
        """英語の確認プロンプトメッセージ"""
        with patch("speedtest_z.main._LANG_JA", False):
            result = _msg("confirm_prompt", count=2, sites="cloudflare, netflix")
            assert "connecting to 2 site(s)" in result
            assert "cloudflare, netflix" in result

    def test_prompt_shown_japanese(self, capsys):
        """日本語ロケールで日本語プロンプトが表示されること"""
        with patch("speedtest_z.main._build_parser") as mock_parser, \
             patch("speedtest_z.main._setup_logging"), \
             patch("speedtest_z.main._find_config", return_value="/tmp/config.ini"), \
             patch("sys.stdin") as mock_stdin, \
             patch("builtins.input", return_value="n"), \
             patch("speedtest_z.main._LANG_JA", True):
            mock_args = MagicMock()
            mock_args.man = False
            mock_args.list_sites = False
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
        """英語ロケールで英語プロンプトが表示されること"""
        with patch("speedtest_z.main._build_parser") as mock_parser, \
             patch("speedtest_z.main._setup_logging"), \
             patch("speedtest_z.main._find_config", return_value="/tmp/config.ini"), \
             patch("sys.stdin") as mock_stdin, \
             patch("builtins.input", return_value="n"), \
             patch("speedtest_z.main._LANG_JA", False):
            mock_args = MagicMock()
            mock_args.man = False
            mock_args.list_sites = False
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
