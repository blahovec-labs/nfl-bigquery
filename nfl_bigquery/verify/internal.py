"""Internal consistency checks + the headline plays->weekly reconciliation.

All checks run in BigQuery and are scoped to a single `season`.
"""
from __future__ import annotations

import logging

from nfl_bigquery.verify.base import VerificationResult

log = logging.getLogger(__name__)


def duplicate_plays_sql(plays_ref: str) -> str:
    return (
        f"SELECT COUNT(*) AS cnt FROM ("
        f"  SELECT game_id, play_id FROM `{plays_ref}` WHERE season = @season"
        f"  GROUP BY game_id, play_id HAVING COUNT(*) > 1)"
    )


def orphan_plays_sql(plays_ref: str, games_ref: str) -> str:
    return (
        f"SELECT COUNT(*) AS cnt FROM `{plays_ref}` p "
        f"LEFT JOIN `{games_ref}` g USING (game_id) "
        f"WHERE p.season = @season AND g.game_id IS NULL"
    )


def reconcile_passing_yards_sql(plays_ref: str, stats_ref: str) -> str:
    return (
        f"WITH plays AS ("
        f"  SELECT passer_player_id AS player_id, SUM(passing_yards) AS yds"
        f"  FROM `{plays_ref}` WHERE season = @season AND passer_player_id IS NOT NULL"
        f"  GROUP BY player_id),"
        f"weekly AS ("
        f"  SELECT player_id, SUM(passing_yards) AS yds"
        f"  FROM `{stats_ref}` WHERE season = @season GROUP BY player_id)"
        f"SELECT COALESCE(SUM(ABS(COALESCE(p.yds,0) - COALESCE(w.yds,0))), 0) AS diff "
        f"FROM plays p FULL OUTER JOIN weekly w USING (player_id)"
    )


def _scalar(client: object, sql: str, season: int, attr: str) -> float:
    from google.cloud import bigquery

    job = client.query(  # type: ignore[union-attr]
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("season", "INT64", season)],
        ),
    )
    rows = list(job.result())
    return float(getattr(rows[0], attr)) if rows else 0.0


def run_internal(
    client: object,
    *,
    plays_ref: str,
    games_ref: str,
    stats_ref: str,
    season: int,
    tolerance: float,
) -> list[VerificationResult]:
    results: list[VerificationResult] = []

    dups = _scalar(client, duplicate_plays_sql(plays_ref), season, "cnt")
    results.append(VerificationResult(
        "no_duplicate_plays", dups == 0,
        f"{int(dups)} duplicate (game_id, play_id) groups",
    ))

    orphans = _scalar(client, orphan_plays_sql(plays_ref, games_ref), season, "cnt")
    results.append(VerificationResult(
        "no_orphan_plays", orphans == 0,
        f"{int(orphans)} plays with no matching game",
    ))

    diff = _scalar(client, reconcile_passing_yards_sql(plays_ref, stats_ref), season, "diff")
    results.append(VerificationResult(
        "passing_yards_reconcile", diff <= tolerance,
        f"total abs passing-yards diff plays vs weekly = {diff:.1f} (tol {tolerance})",
    ))

    return results
