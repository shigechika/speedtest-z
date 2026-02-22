"""JSON/CSV 出力 (--output) のテスト"""

import csv
import io
import json

from speedtest_z.output import OutputCollector


class TestOutputCollector:
    """OutputCollector のテスト"""

    def _sample_data(self):
        """テスト用データ"""
        return [
            {"host": "speedtest-agent", "key": "cloudflare.download", "value": "150.3"},
            {"host": "speedtest-agent", "key": "cloudflare.upload", "value": "45.7"},
        ]

    def test_add_records(self):
        """add() でレコードが蓄積される"""
        collector = OutputCollector("json")
        collector.add(self._sample_data())
        assert len(collector._records) == 2
        assert collector._records[0]["key"] == "cloudflare.download"
        assert collector._records[1]["value"] == "45.7"

    def test_add_includes_timestamp(self):
        """add() で timestamp が追加される"""
        collector = OutputCollector("json")
        collector.add(self._sample_data())
        assert "timestamp" in collector._records[0]
        # ISO 8601 形式
        assert "T" in collector._records[0]["timestamp"]

    def test_multiple_add(self):
        """複数回 add() でレコードが累積"""
        collector = OutputCollector("json")
        collector.add(self._sample_data())
        collector.add([{"host": "h", "key": "netflix.download", "value": "100"}])
        assert len(collector._records) == 3

    def test_flush_json(self, capsys):
        """JSON 出力が正しくフォーマットされる"""
        collector = OutputCollector("json")
        collector.add(self._sample_data())
        collector.flush()
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["key"] == "cloudflare.download"

    def test_flush_csv(self, capsys):
        """CSV 出力にヘッダーとデータが含まれる"""
        collector = OutputCollector("csv")
        collector.add(self._sample_data())
        collector.flush()
        captured = capsys.readouterr()
        reader = csv.DictReader(io.StringIO(captured.out))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["key"] == "cloudflare.download"
        assert rows[0]["value"] == "150.3"
        assert "timestamp" in rows[0]

    def test_flush_csv_empty(self, capsys):
        """空のコレクターで CSV flush しても何も出力しない"""
        collector = OutputCollector("csv")
        collector.flush()
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_flush_json_empty(self, capsys):
        """空のコレクターで JSON flush すると空配列"""
        collector = OutputCollector("json")
        collector.flush()
        captured = capsys.readouterr()
        assert json.loads(captured.out) == []

    def test_host_fallback_empty(self):
        """host キーがない場合は空文字"""
        collector = OutputCollector("json")
        collector.add([{"key": "test.key", "value": "42"}])
        assert collector._records[0]["host"] == ""


class TestCliOutputFlag:
    """CLI --output フラグのテスト"""

    def test_output_default_zabbix(self):
        """デフォルトは zabbix"""
        from speedtest_z.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args([])
        assert args.output == "zabbix"

    def test_output_json(self):
        """--output json"""
        from speedtest_z.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["--output", "json"])
        assert args.output == "json"

    def test_output_csv(self):
        """-o csv"""
        from speedtest_z.cli import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["-o", "csv"])
        assert args.output == "csv"
