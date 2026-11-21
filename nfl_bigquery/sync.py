"""sync orchestration: per-season fetch → transform → write for the 3 fact tables."""
from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime

from nfl_bigquery.games.schema import GAMES_PARTITION, GAMES_SCHEMA
from nfl_bigquery.games.transform import transform_schedules
from nfl_bigquery.plays.schema import PLAYS_PARTITION, PLAYS_SCHEMA
from nfl_bigquery.plays.transform import transform_pbp
from nfl_bigquery.runs import parse_seasons
from nfl_bigquery.schema import to_bq_schema
from nfl_bigquery.stats.schema import WEEKLY_STATS_PARTITION, WEEKLY_STATS_SCHEMA
from nfl_bigquery.stats.transform import transform_player_stats
from nfl_bigquery.writer import TableRef

log = logging.getLogger(__name__)


def current_season() -> int:
    # NFL season labeled by the year it starts; new season rolls over in September.
    now = datetime.now(UTC)
    return now.year if now.month >= 9 else now.year - 1


def _default_ref(base: TableRef, suffix: str) -> str:
    return f"{base.project}.{base.dataset}.{suffix}"


def run_sync(ns: argparse.Namespace, *, client, writer, runs) -> int:
    pbp_ref = TableRef.parse(ns.pbp_table)
    games_ref = TableRef.parse(ns.games_table or _default_ref(pbp_ref, "games"))
    stats_ref = TableRef.parse(
        ns.weekly_stats_table or _default_ref(pbp_ref, "weekly_player_stats"))
    runs_ref = TableRef.parse(ns.runs_table or _default_ref(pbp_ref, "_nfl_ingest_runs"))

    seasons = parse_seasons(ns.seasons, current_season())
    log.info("sync seasons=%s", seasons)

    if ns.dry_run:
        print(f"[dry-run] would sync seasons {seasons} into "
              f"{pbp_ref}, {games_ref}, {stats_ref}")
        return 0

    for ref, schema, part in (
        (pbp_ref, PLAYS_SCHEMA, PLAYS_PARTITION),
        (games_ref, GAMES_SCHEMA, GAMES_PARTITION),
        (stats_ref, WEEKLY_STATS_SCHEMA, WEEKLY_STATS_PARTITION),
    ):
        if ref is games_ref and ns.skip_games:
            continue
        if ref is stats_ref and ns.skip_weekly_stats:
            continue
        writer.create_table_if_missing(ref, to_bq_schema(schema), part)
    runs.create_table_if_missing(runs_ref)

    done = runs.completed_seasons(ref=runs_ref) if ns.resume else set()

    failed: list[int] = []
    for season in seasons:
        if season in done:
            log.info("resume: skipping season %s", season)
            continue
        try:
            counts: dict[str, int] = {}
            counts["plays"] = writer.write_season(
                pbp_ref, transform_pbp(client.load_pbp(season)), season=season)
            if not ns.skip_games:
                counts["games"] = writer.write_season(
                    games_ref, transform_schedules(client.load_schedules(season)), season=season)
            if not ns.skip_weekly_stats:
                counts["weekly_stats"] = writer.write_season(
                    stats_ref, transform_player_stats(client.load_player_stats(season)),
                    season=season)
            if sum(counts.values()) == 0:
                runs.record_empty(ref=runs_ref, season=season)
            else:
                runs.record_success(ref=runs_ref, season=season, rows_written=counts)
        except Exception as e:  # noqa: BLE001 - one bad season must not abort the backfill
            log.exception("season %s failed", season)
            runs.record_failed(ref=runs_ref, season=season, error=str(e)[:1000])
            failed.append(season)
    if failed:
        # Keep going past a bad season, but exit non-zero so the job alerts.
        log.error("sync finished with %d failed season(s): %s", len(failed), failed)
        return 1
    return 0
