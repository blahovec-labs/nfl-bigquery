from unittest.mock import MagicMock, patch

import pandas as pd

from nfl_bigquery.cli import build_parser
from nfl_bigquery.players.sync import run_players


def test_players_dry_run():
    ns = build_parser().parse_args(
        ["players", "--players-table", "p.d.dim_players", "--dry-run"])
    client = MagicMock()
    rc = run_players(ns, client=client, bq_client=MagicMock())
    assert rc == 0
    assert not client.load_players.called


def test_players_upserts():
    ns = build_parser().parse_args(["players", "--players-table", "p.d.dim_players"])
    client = MagicMock()
    client.load_players.return_value = pd.DataFrame({"gsis_id": ["00-1"]})
    bq = MagicMock()
    with patch("nfl_bigquery.players.sync.upsert_players", return_value=1) as up:
        rc = run_players(ns, client=client, bq_client=bq)
    assert rc == 0
    assert up.called
