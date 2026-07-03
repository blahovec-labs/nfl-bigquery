# nfl_bigquery/runs.py
"""Season-keyed run log for resumable syncs. One row per (season) attempt;
--resume skips seasons recorded 'success' or 'empty'.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from nfl_bigquery._version import __version__
from nfl_bigquery.writer import TableRef

log = logging.getLogger(__name__)


def parse_seasons(arg: str, current_season: int) -> list[int]:
    """Expand '1999-2025' | '2023,2025' | '2024' | 'latest' into a list of ints."""
    arg = arg.strip().lower()
    if arg == "latest":
        return [current_season]
    if "-" in arg and "," not in arg:
        lo, hi = arg.split("-", 1)
        return list(range(int(lo), int(hi) + 1))
    return [int(p) for p in arg.split(",") if p.strip()]


@dataclass
class RunsTable:
    client: bigquery.Client

    def create_table_if_missing(self, ref: TableRef) -> None:
        try:
            self.client.get_table(str(ref))
            return
        except NotFound:
            pass
        schema = [
            bigquery.SchemaField("season", "INT64", mode="REQUIRED"),
            bigquery.SchemaField("status", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("rows_written_plays", "INT64"),
            bigquery.SchemaField("rows_written_games", "INT64"),
            bigquery.SchemaField("rows_written_weekly_stats", "INT64"),
            bigquery.SchemaField("error", "STRING"),
            bigquery.SchemaField("run_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("library_version", "STRING"),
        ]
        self.client.create_table(bigquery.Table(str(ref), schema=schema))
        log.info("created runs table %s", ref)

    def completed_seasons(self, *, ref: TableRef) -> set[int]:
        sql = f"SELECT season FROM `{ref}` WHERE status IN ('success', 'empty')"
        return {r.season for r in self.client.query(sql).result()}

    def record_success(self, *, ref: TableRef, season: int, rows_written: dict[str, int]) -> None:
        self._record(ref=ref, season=season, status="success",
                     rows_written=rows_written, error=None)

    def record_empty(self, *, ref: TableRef, season: int) -> None:
        self._record(ref=ref, season=season, status="empty", rows_written={}, error=None)

    def record_failed(self, *, ref: TableRef, season: int, error: str) -> None:
        self._record(ref=ref, season=season, status="failed", rows_written={}, error=error)

    def _record(self, *, ref: TableRef, season: int, status: str,
                rows_written: dict[str, int], error: str | None) -> None:
        row = {
            "season": season,
            "status": status,
            "rows_written_plays": rows_written.get("plays"),
            "rows_written_games": rows_written.get("games"),
            "rows_written_weekly_stats": rows_written.get("weekly_stats"),
            "error": error,
            "run_at": datetime.now(UTC).isoformat(),
            "library_version": __version__,
        }
        errors = self.client.insert_rows_json(str(ref), [row])
        if errors:
            log.warning("runs insert errors: %s", errors)
