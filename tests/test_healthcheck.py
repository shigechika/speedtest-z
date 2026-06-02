"""Tests for the health check (--check)."""

import urllib.error
from unittest.mock import MagicMock, patch

from speedtest_z.healthcheck import SITE_URLS, _check_url, check_sites


class TestCheckUrl:
    """Tests for _check_url()."""

    def test_success_head(self):
        """Return (200, "OK") when HEAD succeeds."""
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
        """Fall back to GET when HEAD returns 405."""
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
        """HTTP errors (other than 405) immediately return the error code."""
        with patch(
            "speedtest_z.healthcheck.urllib.request.urlopen",
            side_effect=urllib.error.HTTPError("url", 503, "Service Unavailable", {}, None),
        ):
            status, reason = _check_url("https://example.com/")
        assert status == 503

    def test_network_error(self):
        """Network errors return (0, error string)."""
        with patch(
            "speedtest_z.healthcheck.urllib.request.urlopen",
            side_effect=Exception("Connection refused"),
        ):
            status, reason = _check_url("https://example.com/")
        assert status == 0
        assert "Connection refused" in reason


class TestCheckSites:
    """Tests for check_sites()."""

    def test_all_ok_returns_0(self, capsys):
        """Return 0 when all sites are OK."""
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
        # All sites are included in the output
        for site in SITE_URLS:
            assert site in captured.out

    def test_failure_returns_1(self, capsys):
        """Return 1 if even one site fails."""
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
        """Check only specific sites."""
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
        # Unspecified sites are not in the output
        assert "ookla" not in captured.out

    def test_unknown_site(self, capsys):
        """An unknown site name results in FAIL."""
        result = check_sites(["nonexistent"])
        assert result == 1
        captured = capsys.readouterr()
        assert "Unknown site" in captured.out

    def test_site_urls_has_all_sites(self):
        """SITE_URLS matches AVAILABLE_SITES."""
        from speedtest_z.sites import AVAILABLE_SITES

        assert set(SITE_URLS.keys()) == set(AVAILABLE_SITES)


class TestCliCheckFlag:
    """Tests for the CLI --check flag."""

    def test_check_flag_parsed(self):
        """The --check flag is parsed."""
        from speedtest_z.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["--check"])
        assert args.check is True

    def test_check_default_false(self):
        """check defaults to False."""
        from speedtest_z.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args([])
        assert args.check is False

    def test_check_with_sites(self):
        """Sites can be specified with --check cloudflare netflix."""
        from speedtest_z.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["--check", "cloudflare", "netflix"])
        assert args.check is True
        assert args.sites == ["cloudflare", "netflix"]
