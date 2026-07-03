"""Schema-drift guard: fixture columns must exactly match PLAYS_SCHEMA names.

Both were generated from the same nflverse release.  If either test fails the
fixture and the dictionary have drifted — DO NOT weaken the assertion; fix the
source of truth (scripts/refresh_dictionaries.py + scripts/make_fixtures.py).
"""
import pandas as pd

from nfl_bigquery.plays.schema import PLAYS_SCHEMA
from nfl_bigquery.schema import spec_names

FIX = "tests/fixtures"


def test_every_pbp_fixture_column_has_a_spec():
    raw = pd.read_parquet(f"{FIX}/pbp_2023_sample.parquet")
    spec_cols = set(spec_names(PLAYS_SCHEMA)) - {"ingested_at"}
    missing = set(raw.columns) - spec_cols
    assert not missing, f"nflverse columns with no ColumnSpec (dictionary drift): {sorted(missing)}"


def test_no_orphan_specs_beyond_source():
    raw = pd.read_parquet(f"{FIX}/pbp_2023_sample.parquet")
    spec_cols = set(spec_names(PLAYS_SCHEMA)) - {"ingested_at"}
    orphans = spec_cols - set(raw.columns)
    assert not orphans, f"ColumnSpecs with no matching nflverse column: {sorted(orphans)}"
