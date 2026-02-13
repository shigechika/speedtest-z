"""CLI パーサーのテスト"""

from unittest.mock import patch, MagicMock

from speedtest_z.main import _build_parser, main, AVAILABLE_SITES


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


class TestMainListSites:
    """main() の --list-sites 分岐テスト"""

    def test_list_sites_output(self, capsys):
        """--list-sites でサイト一覧を出力して終了"""
        with patch("speedtest_z.main._build_parser") as mock_parser:
            mock_args = MagicMock()
            mock_args.list_sites = True
            mock_parser.return_value.parse_args.return_value = mock_args
            main()

        captured = capsys.readouterr()
        assert "Available test sites:" in captured.out
        for site in AVAILABLE_SITES:
            assert site in captured.out
