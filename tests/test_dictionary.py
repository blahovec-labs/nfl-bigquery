import pytest

from nfl_bigquery.dictionary import build_specs, map_bq_type


def test_type_mapping():
    assert map_bq_type("numeric", "epa", {}) == "FLOAT64"
    assert map_bq_type("integer", "week", {}) == "INT64"
    assert map_bq_type("character", "posteam", {}) == "STRING"
    assert map_bq_type("logical", "aborted_play", {}) == "BOOL"


def test_type_override_wins():
    assert map_bq_type("character", "game_date", {"game_date": "DATE"}) == "DATE"


def test_unknown_type_raises():
    with pytest.raises(ValueError):
        map_bq_type("blob", "x", {})


def test_build_specs_from_mini_fixture():
    specs = build_specs("mini_pbp", dict_dir="tests/fixtures")
    by_name = {s.name for s in specs}
    assert {"game_id", "season", "epa"} <= by_name
    epa = next(s for s in specs if s.name == "epa")
    assert epa.type == "FLOAT64"
    assert epa.business_definition  # seeded from description


def test_enrichment_overlay_merges():
    enrichment = {"epa": {
        "semantic_tags": ["metric", "modeled"],
        "valid_range": (-15.0, 15.0),
        "gotchas": ["Null on no-play rows."],
    }}
    specs = build_specs("mini_pbp", dict_dir="tests/fixtures", enrichment=enrichment)
    epa = next(s for s in specs if s.name == "epa")
    assert epa.semantic_tags == ["metric", "modeled"]
    assert epa.valid_range == (-15.0, 15.0)
    assert epa.gotchas == ["Null on no-play rows."]
