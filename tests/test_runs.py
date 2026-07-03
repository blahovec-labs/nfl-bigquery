# tests/test_runs.py
from unittest.mock import MagicMock

from google.cloud import bigquery

from nfl_bigquery.runs import RunsTable, parse_seasons
from nfl_bigquery.writer import TableRef


def test_parse_seasons_range():
    assert parse_seasons("1999-2001", 2026) == [1999, 2000, 2001]


def test_parse_seasons_list():
    assert parse_seasons("2023,2025", 2026) == [2023, 2025]


def test_parse_seasons_latest():
    assert parse_seasons("latest", 2026) == [2026]


def test_parse_seasons_single():
    assert parse_seasons("2024", 2026) == [2024]


def test_completed_seasons_reads_success_and_empty():
    c = MagicMock(spec=bigquery.Client)
    rows = [MagicMock(season=2020), MagicMock(season=2021)]
    c.query.return_value.result.return_value = rows
    rt = RunsTable(client=c)
    got = rt.completed_seasons(ref=TableRef.parse("p.d._nfl_ingest_runs"))
    assert got == {2020, 2021}
    assert "status IN ('success', 'empty')" in c.query.call_args[0][0]


def test_record_success_inserts_row():
    c = MagicMock(spec=bigquery.Client)
    c.insert_rows_json.return_value = []
    rt = RunsTable(client=c)
    rt.record_success(ref=TableRef.parse("p.d._nfl_ingest_runs"), season=2023,
                      rows_written={"plays": 48000, "games": 285, "weekly_stats": 5000})
    row = c.insert_rows_json.call_args[0][1][0]
    assert row["season"] == 2023
    assert row["status"] == "success"
    assert row["rows_written_plays"] == 48000
