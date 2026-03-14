"""Tests for speedtest_z.sites package initialization."""

from speedtest_z.sites import AVAILABLE_SITES, get_site_runners


class TestSitesInit:
    """Tests for AVAILABLE_SITES and get_site_runners()."""

    def test_available_sites_contains_all_expected(self):
        """AVAILABLE_SITES lists all 8 supported sites."""
        expected = [
            "cloudflare",
            "netflix",
            "google",
            "ookla",
            "boxtest",
            "mlab",
            "usen",
            "inonius",
        ]
        for site in expected:
            assert site in AVAILABLE_SITES

    def test_available_sites_count(self):
        """AVAILABLE_SITES has exactly 8 entries."""
        assert len(AVAILABLE_SITES) == 8

    def test_get_site_runners_returns_all_sites(self):
        """get_site_runners() returns a callable for each available site."""
        runners = get_site_runners()
        for site in AVAILABLE_SITES:
            assert site in runners
            assert callable(runners[site])

    def test_get_site_runners_correct_functions(self):
        """get_site_runners() maps to the correct run_xxx functions."""
        runners = get_site_runners()
        assert runners["cloudflare"].__name__ == "run_cloudflare"
        assert runners["netflix"].__name__ == "run_netflix"
        assert runners["google"].__name__ == "run_google"
        assert runners["ookla"].__name__ == "run_ookla"
        assert runners["boxtest"].__name__ == "run_boxtest"
        assert runners["mlab"].__name__ == "run_mlab"
        assert runners["usen"].__name__ == "run_usen"
        assert runners["inonius"].__name__ == "run_inonius"
