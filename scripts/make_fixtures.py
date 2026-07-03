"""Generate small parquet fixtures from nflverse for offline unit tests.

pbp: one game from 2023. schedules: 2023 week 1. players: first 50.
player_stats: 2023 week 1. Run: `python scripts/make_fixtures.py`.
"""
from __future__ import annotations

from pathlib import Path

import nflreadpy as nfl
from _norton_ssl import patch_nflreadpy_session_if_windows

OUT = Path("tests/fixtures")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    patch_nflreadpy_session_if_windows()

    pbp = nfl.load_pbp([2023]).to_pandas()
    one_game = pbp["game_id"].dropna().iloc[0]
    pbp[pbp["game_id"] == one_game].to_parquet(OUT / "pbp_2023_sample.parquet")

    sched = nfl.load_schedules([2023]).to_pandas()
    sched[sched["week"] == 1].to_parquet(OUT / "schedules_2023_sample.parquet")

    players = nfl.load_players().to_pandas().head(50)
    players.to_parquet(OUT / "players_2023_sample.parquet")

    stats = nfl.load_player_stats([2023]).to_pandas()
    stats[stats["week"] == 1].to_parquet(OUT / "player_stats_2023_sample.parquet")
    print("fixtures written")


if __name__ == "__main__":
    main()
