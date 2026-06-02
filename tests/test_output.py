"""Tests for JSON/CSV output (--output)."""

import csv
import io
import json

from speedtest_z.output import OutputCollector


class TestOutputCollector:
    """Tests for OutputCollector."""

    def _sample_data(self):
        """Test data."""
        return [
            {"host": "speedtest-agent", "key": "cloudflare.download", "value": "150.3"},
            {"host": "speedtest-agent", "key": "cloudflare.upload", "value": "45.7"},
        ]

    def test_add_records(self):
        """Records accumulate via add()."""
        collector = OutputCollector("json")
        collector.add(self._sample_data())
        assert len(collector._records) == 2
        assert collector._records[0]["key"] == "cloudflare.download"
        assert collector._records[1]["value"] == "45.7"

    def test_add_includes_timestamp(self):
        """add() adds a timestamp."""
        collector = OutputCollector("json")
        collector.add(self._sample_data())
        assert "timestamp" in collector._records[0]
        # ISO 8601 format
        assert "T" in collector._records[0]["timestamp"]

    def test_multiple_add(self):
        """Records accumulate across multiple add() calls."""
        collector = OutputCollector("json")
        collector.add(self._sample_data())
        collector.add([{"host": "h", "key": "netflix.download", "value": "100"}])
        assert len(collector._records) == 3

    def test_flush_json(self, capsys):
        """JSON output is formatted correctly."""
        collector = OutputCollector("json")
        collector.add(self._sample_data())
        collector.flush()
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["key"] == "cloudflare.download"

    def test_flush_csv(self, capsys):
        """CSV output includes a header and data."""
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
        """Flushing CSV on an empty collector outputs nothing."""
        collector = OutputCollector("csv")
        collector.flush()
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_flush_json_empty(self, capsys):
        """Flushing JSON on an empty collector yields an empty array."""
        collector = OutputCollector("json")
        collector.flush()
        captured = capsys.readouterr()
        assert json.loads(captured.out) == []

    def test_host_fallback_empty(self):
        """An empty string is used when the host key is absent."""
        collector = OutputCollector("json")
        collector.add([{"key": "test.key", "value": "42"}])
        assert collector._records[0]["host"] == ""


class TestCliOutputFlag:
    """Tests for the CLI --output flag."""

    def test_output_default_zabbix(self):
        """The default is zabbix."""
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
