from nfl_bigquery.docs.renderers import render_bq_apply, render_llm, render_markdown
from nfl_bigquery.docs.taxonomy import TABLES


def test_taxonomy_has_all_tables():
    assert set(TABLES) == {"nfl_plays", "games", "weekly_player_stats", "dim_players"}


def test_llm_render_mentions_epa():
    out = render_llm(TABLES)
    assert "nfl_plays" in out
    assert "epa" in out


def test_bq_apply_returns_name_description_pairs():
    pairs = render_bq_apply("nfl_plays", "p.d.nfl_plays")
    names = {n for n, _ in pairs}
    assert "epa" in names
    assert all(isinstance(d, str) for _, d in pairs)


def test_markdown_has_table_headers():
    out = render_markdown(TABLES)
    assert "## nfl_plays" in out
