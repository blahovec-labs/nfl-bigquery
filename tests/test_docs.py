from nfl_bigquery.docs.renderers import (
    render_bq_apply,
    render_dbt,
    render_dictionary_rows,
    render_llm,
    render_markdown,
)
from nfl_bigquery.docs.taxonomy import TABLES


def test_taxonomy_has_all_tables():
    assert set(TABLES) == {"nfl_plays", "games", "weekly_player_stats", "dim_players"}


def test_llm_render_mentions_epa():
    out = render_llm(TABLES)
    assert "nfl_plays" in out
    assert "epa" in out


def test_bq_apply_returns_name_description_pairs():
    pairs = render_bq_apply("nfl_plays")
    names = {n for n, _ in pairs}
    assert "epa" in names
    assert all(isinstance(d, str) for _, d in pairs)


def test_markdown_has_table_headers():
    out = render_markdown(TABLES)
    assert "## nfl_plays" in out


def test_dictionary_rows_have_expected_keys():
    rows = render_dictionary_rows(TABLES)
    assert rows
    assert {"table_name", "column_name", "data_type", "mode",
            "short_description", "business_definition",
            "semantic_tags", "gotchas"} <= rows[0].keys()
    assert any(r["table_name"] == "nfl_plays" for r in rows)


def test_dbt_render_structure():
    out = render_dbt(TABLES)
    assert out.startswith("version: 2")
    assert "  - name: nfl_plays" in out
    assert "  - name: dim_players" in out
    # description lines are safely quoted (json.dumps) — valid even with embedded quotes
    assert '    description: "' in out
