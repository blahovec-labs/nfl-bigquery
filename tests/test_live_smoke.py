# tests/test_live_smoke.py
import pytest

pytestmark = pytest.mark.network


def test_load_one_season_shapes():
    from nfl_bigquery.client import NflverseClient

    c = NflverseClient()
    pbp = c.load_pbp(2023)
    assert len(pbp) > 40000
    assert "epa" in pbp.columns
