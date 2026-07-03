# nfl_bigquery/client.py
"""Thin nflreadpy wrapper: fetch a season's parquet, convert to pandas, retry."""
from __future__ import annotations

import logging
import time

import nflreadpy as nfl
import pandas as pd

log = logging.getLogger(__name__)


class NflverseClient:
    def __init__(self, max_retries: int = 5, backoff_seconds: float = 2.0) -> None:
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds

    def _retry(self, fn, *args):
        last: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return fn(*args).to_pandas()
            except Exception as e:  # noqa: BLE001 - retry any transient download error
                last = e
                wait = self.backoff_seconds * (2 ** (attempt - 1))
                log.warning(
                    "nflverse load failed (attempt %d/%d): %s; retrying in %.1fs",
                    attempt,
                    self.max_retries,
                    e,
                    wait,
                )
                time.sleep(wait)
        raise RuntimeError(f"nflverse load failed after {self.max_retries} attempts") from last

    def load_pbp(self, season: int) -> pd.DataFrame:
        return self._retry(nfl.load_pbp, [season])

    def load_schedules(self, season: int) -> pd.DataFrame:
        return self._retry(nfl.load_schedules, [season])

    def load_player_stats(self, season: int) -> pd.DataFrame:
        return self._retry(nfl.load_player_stats, [season])

    def load_players(self) -> pd.DataFrame:
        return self._retry(nfl.load_players)
