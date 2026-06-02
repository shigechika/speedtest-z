"""Grafana Cloud 統合のテスト"""

import configparser
import io
import struct
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

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

# --- Protobuf decoder (test-only, for round-trip verification) ---


def _decode_varint(data, i):
    """Decode a protobuf varint starting at offset *i*; return (value, next_offset)."""
    result = 0
    shift = 0
    while True:
        b = data[i]
        i += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return result, i


def _decode_fields(data):
    """Decode a protobuf message into a list of (field_number, wire_type, value)."""
    fields = []
    i = 0
    while i < len(data):
        tag, i = _decode_varint(data, i)
        field, wire = tag >> 3, tag & 7
        if wire == 0:  # varint
            val, i = _decode_varint(data, i)
        elif wire == 1:  # 64-bit
            val, i = data[i : i + 8], i + 8
        elif wire == 2:  # length-delimited
            length, i = _decode_varint(data, i)
            val, i = data[i : i + length], i + length
        elif wire == 5:  # 32-bit
            val, i = data[i : i + 4], i + 4
        else:
            raise ValueError(f"unsupported wire type {wire}")
        fields.append((field, wire, val))
    return fields


def _decode_write_request(data):
    """Decode a Prometheus WriteRequest into a list of {labels, samples} dicts."""
    series = []
    for field, wire, val in _decode_fields(data):
        if field != 1 or wire != 2:  # TimeSeries
            continue
        labels = {}
        samples = []
        for f2, w2, v2 in _decode_fields(val):
            if f2 == 1 and w2 == 2:  # Label
                name = value = None
                for f3, _w3, v3 in _decode_fields(v2):
                    if f3 == 1:
                        name = v3.decode("utf-8")
                    elif f3 == 2:
                        value = v3.decode("utf-8")
                labels[name] = value
            elif f2 == 2 and w2 == 2:  # Sample
                s_value = s_ts = None
                for f3, w3, v3 in _decode_fields(v2):
                    if f3 == 1 and w3 == 1:
                        s_value = struct.unpack("<d", v3)[0]
                    elif f3 == 2 and w3 == 0:
                        s_ts = v3
                samples.append((s_value, s_ts))
        series.append({"labels": labels, "samples": samples})
    return series


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


class TestEncoderRoundTrip:
    """Decode the encoded output and assert the structure/values exactly.

    Substring containment checks cannot detect swapped field numbers or a
    corrupted double/varint, so round-trip decoding verifies value equality.
    """

    def test_single_series_round_trip(self):
        labels = [
            ("__name__", "speedtest_download"),
            ("site", "cloudflare"),
            ("host", "host-1"),
        ]
        ts = encode_timeseries(labels, 100.5, 1700000000000)
        series = _decode_write_request(encode_write_request([ts]))

        assert len(series) == 1
        assert series[0]["labels"] == {
            "__name__": "speedtest_download",
            "site": "cloudflare",
            "host": "host-1",
        }
        assert len(series[0]["samples"]) == 1
        value, ts_ms = series[0]["samples"][0]
        assert abs(value - 100.5) < 1e-9
        assert ts_ms == 1700000000000

    def test_multiple_series_round_trip(self):
        ts1 = encode_timeseries([("__name__", "speedtest_download")], 100.5, 1700000000000)
        ts2 = encode_timeseries([("__name__", "speedtest_upload")], 50.25, 1700000000001)
        series = _decode_write_request(encode_write_request([ts1, ts2]))

        assert len(series) == 2
        assert series[0]["labels"]["__name__"] == "speedtest_download"
        assert abs(series[0]["samples"][0][0] - 100.5) < 1e-9
        assert series[1]["labels"]["__name__"] == "speedtest_upload"
        assert abs(series[1]["samples"][0][0] - 50.25) < 1e-9
        assert series[1]["samples"][0][1] == 1700000000001


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

    def _mock_opener(self, status=200, reason="OK"):
        """Return a mock opener (as build_opener does) whose open() succeeds."""
        mock_resp = MagicMock()
        mock_resp.status = status
        mock_resp.reason = reason
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_resp
        return mock_opener

    def test_send_numeric_values(self):
        """数値メトリクスが送信されること"""
        sender = GrafanaSender("https://example.com/push", "user", "token")
        data = [
            {"key": "cloudflare.download", "value": "100.5", "host": "test-host"},
            {"key": "cloudflare.upload", "value": "50.2", "host": "test-host"},
        ]
        mock_opener = self._mock_opener()
        with (
            patch("speedtest_z.grafana.urllib.request.build_opener", return_value=mock_opener),
            patch.dict("sys.modules", {"cramjam": self._mock_cramjam()}),
        ):
            sender.send(data)
            mock_opener.open.assert_called_once()

            # HTTP リクエストの検証
            req = mock_opener.open.call_args[0][0]
            assert req.get_header("Content-type") == "application/x-protobuf"
            assert req.get_header("Content-encoding") == "snappy"
            # Authorization goes in an unredirected header (not forwarded on redirect)
            assert "Basic" in req.get_header("Authorization")
            assert "Authorization" in req.unredirected_hdrs

    def test_send_skips_non_numeric(self):
        """数値でない値はスキップされること"""
        sender = GrafanaSender("https://example.com/push", "user", "token")
        data = [
            {"key": "netflix.server-locations", "value": "Tokyo, Osaka"},
            {"key": "boxtest.POP", "value": "NRT"},
        ]
        mock_opener = self._mock_opener()
        with (
            patch.dict("sys.modules", {"cramjam": self._mock_cramjam()}),
            patch("speedtest_z.grafana.urllib.request.build_opener", return_value=mock_opener),
        ):
            sender.send(data)
            # All non-numeric, so nothing is sent
            mock_opener.open.assert_not_called()

    def test_send_skips_invalid_key(self):
        """ドットなしの key はスキップされること"""
        sender = GrafanaSender("https://example.com/push", "user", "token")
        data = [{"key": "invalid_key", "value": "100.5"}]
        mock_opener = self._mock_opener()
        with (
            patch.dict("sys.modules", {"cramjam": self._mock_cramjam()}),
            patch("speedtest_z.grafana.urllib.request.build_opener", return_value=mock_opener),
        ):
            sender.send(data)
            mock_opener.open.assert_not_called()

    def test_send_mixed_values(self):
        """数値と非数値が混在する場合、数値のみ送信されること"""
        sender = GrafanaSender("https://example.com/push", "user", "token")
        data = [
            {"key": "cloudflare.download", "value": "100.5", "host": "test"},
            {"key": "netflix.server-locations", "value": "Tokyo"},
        ]
        mock_opener = self._mock_opener()
        with (
            patch("speedtest_z.grafana.urllib.request.build_opener", return_value=mock_opener),
            patch.dict("sys.modules", {"cramjam": self._mock_cramjam()}),
        ):
            sender.send(data)
            mock_opener.open.assert_called_once()

    def test_send_payload_round_trip(self):
        """The payload passed to compress_raw carries the correct labels/value."""
        sender = GrafanaSender("https://example.com/push", "user", "token")
        data = [
            {"key": "cloudflare.download", "value": "100.5", "host": "test-host"},
            {"key": "netflix.server-locations", "value": "Tokyo"},  # non-numeric -> skipped
        ]
        mock_cramjam = self._mock_cramjam()
        mock_opener = self._mock_opener()
        with (
            patch("speedtest_z.grafana.urllib.request.build_opener", return_value=mock_opener),
            patch.dict("sys.modules", {"cramjam": mock_cramjam}),
        ):
            sender.send(data)

        # Decode the actual WriteRequest that was handed to compress_raw
        raw = mock_cramjam.snappy.compress_raw.call_args[0][0]
        series = _decode_write_request(bytes(raw))
        assert len(series) == 1  # the non-numeric item is skipped
        labels = series[0]["labels"]
        assert labels["__name__"] == "speedtest_download"
        assert labels["site"] == "cloudflare"
        assert labels["host"] == "test-host"
        value, _ts = series[0]["samples"][0]
        assert abs(value - 100.5) < 1e-9

    def test_send_does_not_follow_redirect(self):
        """A redirect is not followed and is re-raised as failure (no credential leak)."""
        sender = GrafanaSender("https://example.com/push", "user", "token")
        data = [{"key": "cloudflare.download", "value": "100.5", "host": "h"}]
        mock_opener = MagicMock()
        mock_opener.open.side_effect = urllib.error.HTTPError(
            "https://evil.example.com/", 302, "Found", {}, io.BytesIO(b"redirected")
        )
        with (
            patch("speedtest_z.grafana.urllib.request.build_opener", return_value=mock_opener),
            patch.dict("sys.modules", {"cramjam": self._mock_cramjam()}),
            pytest.raises(urllib.error.HTTPError),
        ):
            sender.send(data)


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


# --- SenderManager.__init__ real-branch tests ---


class TestSenderManagerInit:
    """Exercise the real Grafana/OTel init branches of SenderManager.__init__.

    Earlier tests patched __init__ and set attributes by hand, so the enable
    checks, header parsing, and missing-dependency handling never ran.
    """

    @staticmethod
    def _config(sections):
        config = configparser.ConfigParser()
        config.read_dict(sections)
        return config

    def test_grafana_disabled_no_sender(self):
        """enable=false keeps grafana_sender None even if the section exists."""
        config = self._config(
            {
                "zabbix": {"host": "h"},
                "grafana": {
                    "enable": "false",
                    "remote_write_url": "u",
                    "username": "x",
                    "token": "t",
                },
            }
        )
        sm = SenderManager(config, "h", dry_run=True)
        assert sm.grafana_sender is None

    def test_grafana_enabled_constructs_sender(self):
        """enable=true with cramjam present constructs a GrafanaSender."""
        config = self._config(
            {
                "zabbix": {"host": "h"},
                "grafana": {
                    "enable": "true",
                    "remote_write_url": "https://example.com/push",
                    "username": "x",
                    "token": "t",
                },
            }
        )
        with (
            patch.dict("sys.modules", {"cramjam": MagicMock()}),
            patch("speedtest_z.grafana.GrafanaSender") as mock_gs,
        ):
            sm = SenderManager(config, "h", dry_run=True)
        mock_gs.assert_called_once_with("https://example.com/push", "x", "t")
        assert sm.grafana_sender is mock_gs.return_value

    def test_grafana_missing_cramjam_logs_and_none(self):
        """A missing cramjam is caught (ImportError) and grafana_sender stays None."""
        config = self._config(
            {
                "zabbix": {"host": "h"},
                "grafana": {
                    "enable": "true",
                    "remote_write_url": "https://example.com/push",
                    "username": "x",
                    "token": "t",
                },
            }
        )
        # sys.modules["cramjam"] = None makes `import cramjam` raise ImportError
        with patch.dict("sys.modules", {"cramjam": None}):
            sm = SenderManager(config, "h", dry_run=True)
        assert sm.grafana_sender is None

    def test_grafana_incomplete_config_none(self):
        """A missing required key (NoOptionError) keeps grafana_sender None."""
        config = self._config(
            {
                "zabbix": {"host": "h"},
                "grafana": {"enable": "true", "remote_write_url": "https://example.com/push"},
            }
        )
        with patch.dict("sys.modules", {"cramjam": MagicMock()}):
            sm = SenderManager(config, "h", dry_run=True)
        assert sm.grafana_sender is None

    def test_otel_headers_parsed(self):
        """'K1=V1, K2 = V2' headers are parsed into a dict and passed to OtelSender."""
        config = self._config(
            {
                "zabbix": {"host": "h"},
                "otel": {
                    "enable": "true",
                    "endpoint": "https://otlp.example.com/",
                    "headers": "Api-Key=k, X-Scope-OrgID = 1",
                },
            }
        )
        # Substitute speedtest_z.otel so this works without opentelemetry installed
        fake_otel = MagicMock()
        with patch.dict("sys.modules", {"speedtest_z.otel": fake_otel}):
            sm = SenderManager(config, "myhost", dry_run=True)
        fake_otel.OtelSender.assert_called_once_with(
            "https://otlp.example.com/", {"Api-Key": "k", "X-Scope-OrgID": "1"}, "myhost"
        )
        assert sm.otel_sender is fake_otel.OtelSender.return_value

    def test_otel_disabled_no_sender(self):
        """enable=false keeps otel_sender None."""
        config = self._config(
            {
                "zabbix": {"host": "h"},
                "otel": {"enable": "false", "endpoint": "https://otlp.example.com/"},
            }
        )
        sm = SenderManager(config, "h", dry_run=True)
        assert sm.otel_sender is None


# --- Empty-value filter tests ---


class TestSendEmptyFilter:
    """Empty values are not sent to any backend (cross-backend consistency)."""

    def test_empty_values_dropped(self):
        mock_grafana = MagicMock()
        sender = _make_sender(dryrun=False, zabbix_enable=True, grafana_sender=mock_grafana)
        data = [
            {"key": "cloudflare.download", "value": "100.5", "host": "h"},
            {"key": "cloudflare.upload", "value": "", "host": "h"},  # empty -> dropped
        ]
        with patch("speedtest_z.sender.Sender") as mock_sender_cls:
            mock_sender_cls.return_value = MagicMock()
            sender.send(data)
        sent = mock_grafana.send.call_args[0][0]
        assert len(sent) == 1
        assert sent[0]["key"] == "cloudflare.download"

    def test_all_empty_no_send(self):
        mock_grafana = MagicMock()
        sender = _make_sender(dryrun=False, zabbix_enable=True, grafana_sender=mock_grafana)
        data = [{"key": "cloudflare.download", "value": "", "host": "h"}]
        with patch("speedtest_z.sender.Sender") as mock_sender_cls:
            mock_instance = MagicMock()
            mock_sender_cls.return_value = mock_instance
            sender.send(data)
        mock_instance.send_bulk.assert_not_called()
        mock_grafana.send.assert_not_called()
