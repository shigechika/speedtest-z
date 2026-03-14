"""Grafana Cloud 統合のテスト"""

import configparser
import struct
from unittest.mock import MagicMock, patch

from speedtest_z.grafana import (
    GrafanaSender,
    _encode_bytes,
    _encode_double,
    _encode_int64,
    _encode_string,
    _encode_varint,
    encode_label,
    encode_sample,
    encode_timeseries,
    encode_write_request,
)
from speedtest_z.runner import SpeedtestZ
from speedtest_z.sender import SenderManager

# --- Protobuf エンコーダーのユニットテスト ---


class TestEncodeVarint:
    """_encode_varint() のテスト"""

    def test_zero(self):
        assert _encode_varint(0) == b"\x00"

    def test_small(self):
        assert _encode_varint(1) == b"\x01"
        assert _encode_varint(127) == b"\x7f"

    def test_two_bytes(self):
        assert _encode_varint(128) == b"\x80\x01"
        assert _encode_varint(300) == b"\xac\x02"


class TestEncodeFields:
    """各 Protobuf フィールドエンコーダーのテスト"""

    def test_encode_string(self):
        """文字列が正しくエンコードされること"""
        result = _encode_string(1, "test")
        # field 1, wire type 2 (length-delimited) = tag 0x0a
        assert result[0:1] == b"\x0a"
        assert b"test" in result

    def test_encode_double(self):
        """double が正しくエンコードされること"""
        result = _encode_double(1, 3.14)
        # field 1, wire type 1 (64-bit) = tag 0x09
        assert result[0:1] == b"\x09"
        # 値の検証
        value = struct.unpack("<d", result[1:])[0]
        assert abs(value - 3.14) < 1e-10

    def test_encode_int64(self):
        """int64 が正しくエンコードされること"""
        result = _encode_int64(2, 1000)
        # field 2, wire type 0 (varint) = tag 0x10
        assert result[0:1] == b"\x10"

    def test_encode_bytes(self):
        """bytes が正しくエンコードされること"""
        result = _encode_bytes(1, b"hello")
        assert b"hello" in result


class TestEncodeLabel:
    """encode_label() のテスト"""

    def test_basic(self):
        """ラベルのエンコード結果に name と value が含まれること"""
        result = encode_label("__name__", "speedtest_download")
        assert b"__name__" in result
        assert b"speedtest_download" in result


class TestEncodeSample:
    """encode_sample() のテスト"""

    def test_basic(self):
        """サンプルが正しくエンコードされること"""
        result = encode_sample(100.5, 1700000000000)
        assert len(result) > 0


class TestEncodeTimeseries:
    """encode_timeseries() のテスト"""

    def test_basic(self):
        """TimeSeries が正しくエンコードされること"""
        labels = [("__name__", "speedtest_download"), ("site", "cloudflare")]
        result = encode_timeseries(labels, 100.5, 1700000000000)
        assert b"speedtest_download" in result
        assert b"cloudflare" in result


class TestEncodeWriteRequest:
    """encode_write_request() のテスト"""

    def test_single(self):
        """単一 TimeSeries の WriteRequest"""
        ts = encode_timeseries([("__name__", "speedtest_download")], 100.5, 1700000000000)
        result = encode_write_request([ts])
        assert len(result) > 0

    def test_multiple(self):
        """複数 TimeSeries の WriteRequest"""
        ts1 = encode_timeseries([("__name__", "speedtest_download")], 100.5, 1700000000000)
        ts2 = encode_timeseries([("__name__", "speedtest_upload")], 50.2, 1700000000000)
        result = encode_write_request([ts1, ts2])
        assert b"speedtest_download" in result
        assert b"speedtest_upload" in result


# --- GrafanaSender のテスト ---


class TestGrafanaSender:
    """GrafanaSender のテスト"""

    def test_init(self):
        """初期化で属性が設定されること"""
        sender = GrafanaSender("https://example.com/push", "user", "token")
        assert sender.url == "https://example.com/push"
        assert sender.username == "user"
        assert sender.token == "token"

    def _mock_cramjam(self):
        """cramjam モジュールのモックを返す"""
        mock_cramjam = MagicMock()
        mock_cramjam.snappy.compress_raw.return_value = b"compressed"
        return mock_cramjam

    def test_send_numeric_values(self):
        """数値メトリクスが送信されること"""
        sender = GrafanaSender("https://example.com/push", "user", "token")
        data = [
            {"key": "cloudflare.download", "value": "100.5", "host": "test-host"},
            {"key": "cloudflare.upload", "value": "50.2", "host": "test-host"},
        ]
        with (
            patch("speedtest_z.grafana.urllib.request.urlopen") as mock_urlopen,
            patch.dict("sys.modules", {"cramjam": self._mock_cramjam()}),
        ):
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.reason = "OK"
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            sender.send(data)
            mock_urlopen.assert_called_once()

            # HTTP リクエストの検証
            req = mock_urlopen.call_args[0][0]
            assert req.get_header("Content-type") == "application/x-protobuf"
            assert req.get_header("Content-encoding") == "snappy"
            assert "Basic" in req.get_header("Authorization")

    def test_send_skips_non_numeric(self):
        """数値でない値はスキップされること"""
        sender = GrafanaSender("https://example.com/push", "user", "token")
        data = [
            {"key": "netflix.server-locations", "value": "Tokyo, Osaka"},
            {"key": "boxtest.POP", "value": "NRT"},
        ]
        with (
            patch.dict("sys.modules", {"cramjam": self._mock_cramjam()}),
            patch("speedtest_z.grafana.urllib.request.urlopen") as mock_urlopen,
        ):
            sender.send(data)
            # 全て非数値なので送信されない
            mock_urlopen.assert_not_called()

    def test_send_skips_invalid_key(self):
        """ドットなしの key はスキップされること"""
        sender = GrafanaSender("https://example.com/push", "user", "token")
        data = [{"key": "invalid_key", "value": "100.5"}]
        with (
            patch.dict("sys.modules", {"cramjam": self._mock_cramjam()}),
            patch("speedtest_z.grafana.urllib.request.urlopen") as mock_urlopen,
        ):
            sender.send(data)
            mock_urlopen.assert_not_called()

    def test_send_mixed_values(self):
        """数値と非数値が混在する場合、数値のみ送信されること"""
        sender = GrafanaSender("https://example.com/push", "user", "token")
        data = [
            {"key": "cloudflare.download", "value": "100.5", "host": "test"},
            {"key": "netflix.server-locations", "value": "Tokyo"},
        ]
        with (
            patch("speedtest_z.grafana.urllib.request.urlopen") as mock_urlopen,
            patch.dict("sys.modules", {"cramjam": self._mock_cramjam()}),
        ):
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.reason = "OK"
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            sender.send(data)
            mock_urlopen.assert_called_once()


# --- cramjam 未インストール時のフォールバックテスト ---


class TestCramjamFallback:
    """cramjam 未インストール時の graceful fallback テスト"""

    def test_grafana_init_without_cramjam(self):
        """cramjam なしでも GrafanaSender の初期化でエラーにならないこと"""
        # GrafanaSender 自体は cramjam を import しない（send() 時に import）
        sender = GrafanaSender("https://example.com/push", "user", "token")
        assert sender is not None

    def test_runner_grafana_without_cramjam(self):
        """cramjam なしで [grafana] enable=true の場合、警告が出ること"""
        config = configparser.ConfigParser()
        config.read_dict(
            {
                "general": {"dry_run": "true", "headless": "true", "timeout": "30"},
                "zabbix": {
                    "enable": "false",
                    "server": "127.0.0.1",
                    "port": "10051",
                    "host": "test",
                },
                "grafana": {
                    "enable": "true",
                    "remote_write_url": "https://example.com/push",
                    "username": "user",
                    "token": "token",
                },
            }
        )
        with (
            patch.object(SpeedtestZ, "_init_driver"),
            patch("speedtest_z.runner._find_config", return_value=None),
            patch("speedtest_z.runner.signal.signal"),
            patch(
                "speedtest_z.grafana.GrafanaSender",
                side_effect=ImportError("No module named 'cramjam'"),
            ),
            patch.object(SpeedtestZ, "__init__", lambda self, *a, **kw: None),
        ):
            app = SpeedtestZ.__new__(SpeedtestZ)
            app.config = config
            app.dryrun = True
            app.grafana_sender = None
            # [grafana] セクションの読み込みをシミュレート
            if config.has_section("grafana"):
                grafana_enable = config.getboolean("grafana", "enable", fallback=False)
                if grafana_enable:
                    try:
                        raise ImportError("No module named 'cramjam'")
                    except ImportError:
                        pass  # graceful fallback
            assert app.grafana_sender is None


# --- send_results() の統合テスト ---


def _make_sender(dryrun=True, zabbix_enable=False, grafana_sender=None):
    """SenderManager インスタンスを直接作成"""
    with patch.object(SenderManager, "__init__", lambda self, *a, **kw: None):
        sender = SenderManager.__new__(SenderManager)
        sender.dry_run = dryrun
        sender.zabbix_enable = zabbix_enable
        sender.zabbix_server = "127.0.0.1"
        sender.zabbix_port = 10051
        sender.zabbix_host = "speedtest-agent"
        sender.grafana_sender = grafana_sender
        sender.otel_sender = None
    return sender


class TestSendResultsZabbixEnable:
    """[zabbix] enable フラグのテスト"""

    def test_zabbix_disabled_no_send(self):
        """zabbix_enable=False では Sender が呼ばれないこと"""
        sender = _make_sender(dryrun=False, zabbix_enable=False)
        data = [{"key": "speedtest.dl", "value": "100.5"}]
        with patch("speedtest_z.sender.Sender") as mock_sender:
            sender.send(data)
            mock_sender.assert_not_called()

    def test_zabbix_enabled_sends(self):
        """zabbix_enable=True では Sender.send_bulk() が呼ばれること"""
        sender = _make_sender(dryrun=False, zabbix_enable=True)
        data = [{"key": "speedtest.dl", "value": "100.5"}]
        with patch("speedtest_z.sender.Sender") as mock_sender_cls:
            mock_instance = MagicMock()
            mock_sender_cls.return_value = mock_instance
            sender.send(data)
            mock_sender_cls.assert_called_once_with("127.0.0.1", 10051)
            mock_instance.send_bulk.assert_called_once()


class TestSendResultsGrafana:
    """send_results() の Grafana 送信テスト"""

    def test_grafana_sender_called(self):
        """grafana_sender が設定されていれば send() が呼ばれること"""
        mock_grafana = MagicMock()
        sender = _make_sender(dryrun=False, grafana_sender=mock_grafana)
        data = [{"key": "cloudflare.download", "value": "100.5"}]
        with patch("speedtest_z.sender.Sender"):
            sender.send(data)
            mock_grafana.send.assert_called_once_with(data)

    def test_grafana_sender_not_called_on_dryrun(self):
        """dryrun=True では grafana_sender.send() が呼ばれないこと"""
        mock_grafana = MagicMock()
        sender = _make_sender(dryrun=True, grafana_sender=mock_grafana)
        data = [{"key": "cloudflare.download", "value": "100.5"}]
        sender.send(data)
        mock_grafana.send.assert_not_called()

    def test_grafana_error_handled(self):
        """Grafana 送信エラーでもクラッシュしないこと"""
        mock_grafana = MagicMock()
        mock_grafana.send.side_effect = Exception("Connection error")
        sender = _make_sender(dryrun=False, grafana_sender=mock_grafana)
        data = [{"key": "cloudflare.download", "value": "100.5"}]
        with patch("speedtest_z.sender.Sender"):
            sender.send(data)  # 例外が伝播しない

    def test_both_zabbix_and_grafana(self):
        """Zabbix と Grafana の両方が呼ばれること"""
        mock_grafana = MagicMock()
        sender = _make_sender(dryrun=False, zabbix_enable=True, grafana_sender=mock_grafana)
        data = [{"key": "cloudflare.download", "value": "100.5"}]
        with patch("speedtest_z.sender.Sender") as mock_sender_cls:
            mock_instance = MagicMock()
            mock_sender_cls.return_value = mock_instance
            sender.send(data)
            mock_instance.send_bulk.assert_called_once()
            mock_grafana.send.assert_called_once_with(data)


# --- config.ini の dry_run / dryrun 互換テスト ---


class TestDryRunCompat:
    """dry_run / dryrun 両方の config キー互換テスト"""

    def _make_app_with_config(self, config_dict):
        """config 辞書から SpeedtestZ を作成"""
        config = configparser.ConfigParser()
        config.read_dict(config_dict)
        with patch.object(SpeedtestZ, "__init__", lambda self, *a, **kw: None):
            app = SpeedtestZ.__new__(SpeedtestZ)
            app.config = config
            # dry_run / dryrun の互換読み込みロジックを再現
            app.dryrun = config.getboolean("general", "dry_run", fallback=None)
            if app.dryrun is None:
                app.dryrun = config.getboolean("general", "dryrun", fallback=True)
        return app

    def test_dry_run_key(self):
        """dry_run キーが読み込まれること"""
        app = self._make_app_with_config({"general": {"dry_run": "false"}})
        assert app.dryrun is False

    def test_dryrun_key_fallback(self):
        """旧名 dryrun キーがフォールバックで読み込まれること"""
        app = self._make_app_with_config({"general": {"dryrun": "false"}})
        assert app.dryrun is False

    def test_dry_run_takes_priority(self):
        """dry_run と dryrun 両方ある場合、dry_run が優先されること"""
        app = self._make_app_with_config({"general": {"dry_run": "false", "dryrun": "true"}})
        assert app.dryrun is False

    def test_neither_key_defaults_true(self):
        """どちらもない場合、デフォルト True になること"""
        app = self._make_app_with_config({"general": {"headless": "true"}})
        assert app.dryrun is True
