"""Internal consistency checks + the headline plays->weekly reconciliation.

All checks run in BigQuery and are scoped to a single `season`.
"""
from __future__ import annotations

import logging

from nfl_bigquery.verify.base import VerificationResult

log = logging.getLogger(__name__)

# (result_name, plays_col, plays_actor, weekly_col)
RECONCILE_METRICS: list[tuple[str, str, str, str]] = [
    ("passing_yards",   "passing_yards",   "passer_player_id",   "passing_yards"),
    ("rushing_yards",   "rushing_yards",   "rusher_player_id",   "rushing_yards"),
    ("receiving_yards", "receiving_yards", "receiver_player_id", "receiving_yards"),
    ("passing_tds",     "pass_touchdown",  "passer_player_id",   "passing_tds"),
    ("rushing_tds",     "rush_touchdown",  "rusher_player_id",   "rushing_tds"),
    ("receiving_tds",   "pass_touchdown",  "receiver_player_id", "receiving_tds"),
]


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


def reconcile_metric_sql(
    plays_ref: str,
    stats_ref: str,
    *,
    plays_col: str,
    plays_actor: str,
    weekly_col: str,
) -> str:
    return (
        f"WITH plays AS ("
        f"  SELECT {plays_actor} AS player_id, SUM({plays_col}) AS v"
        f"  FROM `{plays_ref}` WHERE season = @season AND {plays_actor} IS NOT NULL"
        f"  GROUP BY player_id),"
        f"weekly AS ("
        f"  SELECT player_id, SUM({weekly_col}) AS v"
        f"  FROM `{stats_ref}` WHERE season = @season GROUP BY player_id)"
        f"SELECT COALESCE(SUM(ABS(COALESCE(p.v,0)-COALESCE(w.v,0))),0) AS diff "
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

    for name, plays_col, plays_actor, weekly_col in RECONCILE_METRICS:
        diff = _scalar(
            client,
            reconcile_metric_sql(
                plays_ref,
                stats_ref,
                plays_col=plays_col,
                plays_actor=plays_actor,
                weekly_col=weekly_col,
            ),
            season,
            "diff",
        )
        results.append(VerificationResult(
            f"{name}_reconcile",
            diff <= tolerance,
            f"total abs {name} diff plays vs weekly = {diff:.1f} (tol {tolerance})",
        ))

    return results
