"""__init__.py のテスト"""

from unittest.mock import patch


class TestVersion:
    """バージョン取得のテスト"""

    def test_version_is_string(self):
        """__version__ が文字列であること"""
        from speedtest_z import __version__

        assert isinstance(__version__, str)

    def test_version_not_empty(self):
        """__version__ が空でないこと"""
        from speedtest_z import __version__

        assert len(__version__) > 0

    def test_version_fallback(self):
        """PackageNotFoundError 時のフォールバック"""
        from importlib.metadata import PackageNotFoundError

        with patch(
            "importlib.metadata.version", side_effect=PackageNotFoundError()
        ):
            # モジュールを再ロード
            import importlib
            import speedtest_z

            importlib.reload(speedtest_z)
            assert speedtest_z.__version__ == "0.0.0"

            # 元に戻す
            importlib.reload(speedtest_z)
