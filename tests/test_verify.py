from unittest.mock import MagicMock

from nfl_bigquery.verify.base import VerificationResult
from nfl_bigquery.verify.internal import (
    duplicate_plays_sql,
    orphan_plays_sql,
    reconcile_passing_yards_sql,
    run_internal,
)


def test_result_repr():
    r = VerificationResult(name="dup", passed=True, detail="0 dups")
    assert r.passed and "dup" in repr(r)


def test_duplicate_sql_groups_by_keys():
    sql = duplicate_plays_sql("p.d.nfl_plays")
    assert "GROUP BY game_id, play_id" in sql
    assert "HAVING COUNT(*) > 1" in sql


def test_orphan_sql_left_joins_games():
    sql = orphan_plays_sql("p.d.nfl_plays", "p.d.games")
    assert "LEFT JOIN" in sql
    assert "p.d.games" in sql
    assert "game_id IS NULL" in sql


def test_reconcile_sql_aggregates_both_sides():
    sql = reconcile_passing_yards_sql("p.d.nfl_plays", "p.d.weekly_player_stats")
    assert "passing_yards" in sql
    assert "p.d.nfl_plays" in sql
    assert "p.d.weekly_player_stats" in sql


def test_run_internal_reports_pass_when_counts_zero():
    client = MagicMock()
    # every check query returns a single row whose .cnt/.mismatch is 0
    row = MagicMock(cnt=0, mismatch=0, diff=0.0)
    client.query.return_value.result.return_value = [row]
    results = run_internal(
        client, plays_ref="p.d.nfl_plays", games_ref="p.d.games",
        stats_ref="p.d.weekly_player_stats", season=2023, tolerance=1.0)
    assert all(r.passed for r in results)
    assert len(results) >= 3
