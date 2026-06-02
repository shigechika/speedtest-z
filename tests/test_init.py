"""Tests for __init__.py."""

import re
from unittest.mock import patch


class TestVersion:
    """Tests for version retrieval."""

    def test_version_is_string(self):
        """__version__ should be a string."""
        from speedtest_z import __version__

        assert isinstance(__version__, str)

    def test_version_not_empty(self):
        """__version__ should not be empty."""
        from speedtest_z import __version__

        assert len(__version__) > 0

    def test_version_fallback(self):
        """On PackageNotFoundError, __version__ falls back to a version string.

        release-please keeps the fallback literal in __init__.py in sync with the
        released version, so assert the semver shape rather than a fixed value.
        """
        from importlib.metadata import PackageNotFoundError

        with patch("importlib.metadata.version", side_effect=PackageNotFoundError()):
            # Reload the module so the fallback branch runs.
            import importlib

            import speedtest_z

            importlib.reload(speedtest_z)
            assert re.match(r"^\d+\.\d+\.\d+", speedtest_z.__version__)

            # Restore the real version.
            importlib.reload(speedtest_z)
