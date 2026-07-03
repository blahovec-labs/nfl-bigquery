from unittest.mock import MagicMock

from nfl_bigquery.cli import build_parser
from nfl_bigquery.sync import _default_ref, run_sync
from nfl_bigquery.writer import TableRef


def test_default_ref():
    assert _default_ref(TableRef.parse("p.d.nfl_plays"), "games") == "p.d.games"


def test_sync_dry_run_touches_nothing():
    parser = build_parser()
    ns = parser.parse_args([
        "sync", "--seasons", "2023", "--pbp-table", "p.d.nfl_plays", "--dry-run",
    ])
    client, writer, runs = MagicMock(), MagicMock(), MagicMock()
    rc = run_sync(ns, client=client, writer=writer, runs=runs)
    assert rc == 0
    assert not client.load_pbp.called
    assert not writer.write_season.called


def test_sync_writes_three_tables_per_season(monkeypatch):
    import pandas as pd
    parser = build_parser()
    ns = parser.parse_args(["sync", "--seasons", "2023", "--pbp-table", "p.d.nfl_plays"])
    client = MagicMock()
    client.load_pbp.return_value = pd.DataFrame({"season": [2023], "game_id": ["g"]})
    client.load_schedules.return_value = pd.DataFrame({"season": [2023]})
    client.load_player_stats.return_value = pd.DataFrame({"season": [2023]})
    writer = MagicMock()
    writer.write_season.return_value = 1
    runs = MagicMock()
    runs.completed_seasons.return_value = set()
    # transforms are exercised for real; align_to_schema handles missing columns
    rc = run_sync(ns, client=client, writer=writer, runs=runs)
    assert rc == 0
    # plays + games + weekly_stats = 3 write_season calls for the one season
    assert writer.write_season.call_count == 3
    runs.record_success.assert_called_once()


def test_sync_resume_skips_completed_season():
    parser = build_parser()
    ns = parser.parse_args([
        "sync", "--seasons", "2023", "--pbp-table", "p.d.nfl_plays", "--resume",
    ])
    client, writer, runs = MagicMock(), MagicMock(), MagicMock()
    runs.completed_seasons.return_value = {2023}
    rc = run_sync(ns, client=client, writer=writer, runs=runs)
    assert rc == 0
    assert not client.load_pbp.called
