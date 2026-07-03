# tests/test_enrichment_keys.py
"""Assert that every enrichment overlay key matches a real field in its dictionary CSV.

Mis-keyed overlay entries are silently ignored by build_specs (enrichment.get(name, {})),
so an off-by-one or renamed key causes silent spec degradation with no error. Spec §11
requires this guard.

The one intentional exception is documented in-line: GAMES_ENRICHMENT has a `gameday`
entry (the pre-rename dictionary field) that maps through the _build() rename to
`game_date` in the final schema. `gameday` IS present in schedules.csv, so the assertion
still passes — no special-casing needed.
"""
from __future__ import annotations

import pytest

from nfl_bigquery.dictionary import load_dictionary
from nfl_bigquery.games.schema import GAMES_ENRICHMENT
from nfl_bigquery.players.schema import DIM_PLAYERS_ENRICHMENT
from nfl_bigquery.plays.enrichment import ENRICHMENT as PLAYS_ENRICHMENT
from nfl_bigquery.stats.schema import WEEKLY_STATS_ENRICHMENT


def _field_set(table: str) -> set[str]:
    df = load_dictionary(table)
    return set(df["field"].str.strip().tolist())


@pytest.mark.parametrize(
    "overlay_name,overlay,table",
    [
        ("PLAYS_ENRICHMENT", PLAYS_ENRICHMENT, "pbp"),
        ("GAMES_ENRICHMENT", GAMES_ENRICHMENT, "schedules"),
        ("WEEKLY_STATS_ENRICHMENT", WEEKLY_STATS_ENRICHMENT, "player_stats"),
        ("DIM_PLAYERS_ENRICHMENT", DIM_PLAYERS_ENRICHMENT, "players"),
    ],
)
def test_enrichment_keys_exist_in_dictionary(
    overlay_name: str, overlay: dict, table: str
) -> None:
    fields = _field_set(table)
    bad = set(overlay) - fields
    assert bad == set(), (
        f"{overlay_name} has key(s) not present in dictionaries/{table}.csv: {sorted(bad)}"
    )
