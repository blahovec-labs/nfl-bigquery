from unittest.mock import MagicMock

from nfl_bigquery.verify.base import VerificationResult
from nfl_bigquery.verify.internal import (
    RECONCILE_METRICS,
    duplicate_plays_sql,
    orphan_plays_sql,
    reconcile_metric_sql,
    run_internal,
)


def test_result_repr():
    r = VerificationResult(name="dup", passed=True, detail="0 dups")
    assert r.passed and "dup" in repr(r)


def test_duplicate_sql_groups_by_keys():
    sql = duplicate_plays_sql("p.d.nfl_plays")
    assert "GROUP BY game_id, play_id" in sql
    assert "HAVING COUNT(*) > 1" in sql
    assert "@season" in sql


def test_orphan_sql_left_joins_games():
    sql = orphan_plays_sql("p.d.nfl_plays", "p.d.games")
    assert "LEFT JOIN" in sql
    assert "p.d.games" in sql
    assert "game_id IS NULL" in sql
    assert "@season" in sql


def test_reconcile_metric_sql_structure():
    sql = reconcile_metric_sql(
        "p.d.nfl_plays",
        "p.d.weekly_player_stats",
        plays_col="rushing_yards",
        plays_actor="rusher_player_id",
        weekly_col="rushing_yards",
    )
    assert "FULL OUTER JOIN" in sql
    assert "ABS(" in sql
    assert "COALESCE(" in sql
    assert "@season" in sql
    assert "rushing_yards" in sql
    assert "rusher_player_id" in sql
    assert "p.d.weekly_player_stats" in sql


def test_reconcile_metrics_cover_all_six():
    names = {m[0] for m in RECONCILE_METRICS}
    assert names == {
        "passing_yards", "rushing_yards", "receiving_yards",
        "passing_tds", "rushing_tds", "receiving_tds",
    }
    # passing_tds and receiving_tds both use pass_touchdown; rushing_tds uses rush_touchdown
    td_plays_col = {m[0]: m[1] for m in RECONCILE_METRICS if m[0].endswith("_tds")}
    assert td_plays_col["passing_tds"] == "pass_touchdown"
    assert td_plays_col["receiving_tds"] == "pass_touchdown"
    assert td_plays_col["rushing_tds"] == "rush_touchdown"


def test_run_internal_reports_pass_when_counts_zero():
    client = MagicMock()
    # every check query returns a single row whose .cnt/.diff is 0
    row = MagicMock(cnt=0, diff=0.0)
    client.query.return_value.result.return_value = [row]
    results = run_internal(
        client, plays_ref="p.d.nfl_plays", games_ref="p.d.games",
        stats_ref="p.d.weekly_player_stats", season=2023, tolerance=1.0)
    assert all(r.passed for r in results)
    assert len(results) == 8


def test_run_internal_reports_fail_when_counts_nonzero():
    client = MagicMock()
    # cnt=2 fails dup/orphan checks; diff=50.0 exceeds tolerance=1.0
    row = MagicMock(cnt=2, diff=50.0)
    client.query.return_value.result.return_value = [row]
    results = run_internal(
        client, plays_ref="p.d.nfl_plays", games_ref="p.d.games",
        stats_ref="p.d.weekly_player_stats", season=2023, tolerance=1.0)
    assert not all(r.passed for r in results)
    assert len(results) == 8
    # dup and orphan checks must both fail
    assert not results[0].passed
    assert not results[1].passed
