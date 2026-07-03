# tests/test_client.py
import pandas as pd

import nfl_bigquery.client as client_mod
from nfl_bigquery.client import NflverseClient


class _FakePolars:
    def __init__(self, pdf): self._pdf = pdf
    def to_pandas(self): return self._pdf


def test_load_pbp_converts_to_pandas(monkeypatch):
    pdf = pd.DataFrame({"game_id": ["2023_01_DET_KC"], "season": [2023]})
    monkeypatch.setattr(client_mod.nfl, "load_pbp", lambda seasons: _FakePolars(pdf))
    out = NflverseClient().load_pbp(2023)
    assert isinstance(out, pd.DataFrame)
    assert out.iloc[0]["season"] == 2023


def test_load_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}
    pdf = pd.DataFrame({"season": [2023]})

    def flaky(seasons):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return _FakePolars(pdf)

    monkeypatch.setattr(client_mod.nfl, "load_schedules", flaky)
    monkeypatch.setattr(client_mod.time, "sleep", lambda s: None)
    out = NflverseClient(max_retries=5).load_schedules(2023)
    assert calls["n"] == 3
    assert len(out) == 1
