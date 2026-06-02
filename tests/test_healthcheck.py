"""ヘルスチェック (--check) のテスト"""

import urllib.error
from unittest.mock import MagicMock, patch

from speedtest_z.healthcheck import SITE_URLS, _check_url, check_sites


class TestCheckUrl:
    """_check_url() のテスト"""

    def test_success_head(self):
        """HEAD 成功時は (200, "OK") を返す"""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.reason = "OK"
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("speedtest_z.healthcheck.urllib.request.urlopen", return_value=mock_resp):
            status, reason = _check_url("https://example.com/")
        assert status == 200
        assert reason == "OK"

    def test_fallback_to_get_on_405(self):
        """HEAD で 405 の場合は GET にフォールバック"""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.reason = "OK"
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = MagicMock(return_value=False)

        def side_effect(req, timeout=10):
            if req.get_method() == "HEAD":
                raise urllib.error.HTTPError(req.full_url, 405, "Method Not Allowed", {}, None)
            return mock_resp

        with patch("speedtest_z.healthcheck.urllib.request.urlopen", side_effect=side_effect):
            status, reason = _check_url("https://example.com/")
        assert status == 200

    def test_fallback_to_get_on_501(self):
        """HEAD returning 501 (Not Implemented) also falls back to GET."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.reason = "OK"
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = MagicMock(return_value=False)

        def side_effect(req, timeout=10):
            if req.get_method() == "HEAD":
                raise urllib.error.HTTPError(req.full_url, 501, "Not Implemented", {}, None)
            return mock_resp

        with patch("speedtest_z.healthcheck.urllib.request.urlopen", side_effect=side_effect):
            status, reason = _check_url("https://example.com/")
        assert status == 200

    def test_http_error(self):
        """HTTP エラー（405以外）は即座にエラーコードを返す"""
        with patch(
            "speedtest_z.healthcheck.urllib.request.urlopen",
            side_effect=urllib.error.HTTPError("url", 503, "Service Unavailable", {}, None),
        ):
            status, reason = _check_url("https://example.com/")
        assert status == 503

    def test_network_error(self):
        """ネットワークエラーは (0, エラー文字列) を返す"""
        with patch(
            "speedtest_z.healthcheck.urllib.request.urlopen",
            side_effect=Exception("Connection refused"),
        ):
            status, reason = _check_url("https://example.com/")
        assert status == 0
        assert "Connection refused" in reason


class TestCheckSites:
    """check_sites() のテスト"""

    def test_all_ok_returns_0(self, capsys):
        """全サイト OK の場合は 0 を返す"""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.reason = "OK"
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("speedtest_z.healthcheck.urllib.request.urlopen", return_value=mock_resp):
            result = check_sites()
        assert result == 0
        captured = capsys.readouterr()
        assert "Site Health Check:" in captured.out
        # 全サイトが出力に含まれる
        for site in SITE_URLS:
            assert site in captured.out

    def test_failure_returns_1(self, capsys):
        """1つでも失敗があれば 1 を返す"""
        with patch(
            "speedtest_z.healthcheck.urllib.request.urlopen",
            side_effect=Exception("timeout"),
        ):
            result = check_sites(["cloudflare"])
        assert result == 1
        captured = capsys.readouterr()
        assert "FAIL" in captured.out

    def test_failure_shows_reason(self, capsys):
        """The failure reason is included in the output."""
        with patch(
            "speedtest_z.healthcheck.urllib.request.urlopen",
            side_effect=Exception("Connection refused"),
        ):
            check_sites(["cloudflare"])
        captured = capsys.readouterr()
        assert "Connection refused" in captured.out

    def test_specific_sites(self, capsys):
        """特定サイトのみチェック"""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.reason = "OK"
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("speedtest_z.healthcheck.urllib.request.urlopen", return_value=mock_resp):
            result = check_sites(["cloudflare", "netflix"])
        assert result == 0
        captured = capsys.readouterr()
        assert "cloudflare" in captured.out
        assert "netflix" in captured.out
        # 指定していないサイトは出力されない
        assert "ookla" not in captured.out

    def test_unknown_site(self, capsys):
        """存在しないサイト名は FAIL"""
        result = check_sites(["nonexistent"])
        assert result == 1
        captured = capsys.readouterr()
        assert "Unknown site" in captured.out

    def test_site_urls_has_all_sites(self):
        """SITE_URLS が AVAILABLE_SITES と一致"""
        from speedtest_z.sites import AVAILABLE_SITES

        assert set(SITE_URLS.keys()) == set(AVAILABLE_SITES)


class TestCliCheckFlag:
    """CLI --check フラグのテスト"""

    def test_check_flag_parsed(self):
        """--check フラグがパースされること"""
        from speedtest_z.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["--check"])
        assert args.check is True

    def test_check_default_false(self):
        """デフォルトで check=False"""
        from speedtest_z.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args([])
        assert args.check is False

    def test_check_with_sites(self):
        """--check cloudflare netflix でサイト指定可能"""
        from speedtest_z.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["--check", "cloudflare", "netflix"])
        assert args.check is True
        assert args.sites == ["cloudflare", "netflix"]
