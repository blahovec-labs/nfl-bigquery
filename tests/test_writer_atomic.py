"""write_season must never leave a season deleted but not replaced.

It ran `DELETE ... WHERE season = @season` as its own query and then a separate
load job. A BigQuery load job can't join a transaction, so those were two commits:
a failed load left the whole season of plays/games/weekly stats gone until the next
successful run. Same failure that wiped 2026-06-02 from statcast-bigquery.

Contract now: load into a short-lived staging table FIRST, then DELETE + INSERT ...
SELECT in ONE multi-statement transaction, then drop the staging table.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest
from google.cloud import bigquery

from nfl_bigquery.writer import BigQueryWriter, TableRef

REF = TableRef.parse("p.d.nfl_plays")
TARGET = "p.d.nfl_plays"
SCHEMA = [bigquery.SchemaField("season", "INT64"), bigquery.SchemaField("play_id", "INT64")]


def _client() -> MagicMock:
    c = MagicMock(spec=bigquery.Client)
    c.project = "p"
    c.get_table.return_value = bigquery.Table(TARGET, schema=SCHEMA)
    return c


def _df() -> pd.DataFrame:
    return pd.DataFrame({"season": [2025, 2025], "play_id": [1, 2]})


def _sql(c: MagicMock) -> list[str]:
    return [call.args[0] for call in c.query_and_wait.call_args_list] + [
        call.args[0] for call in c.query.call_args_list
    ]


def test_failed_load_deletes_nothing():
    c = _client()
    c.load_table_from_dataframe.return_value.result.side_effect = RuntimeError("400 load failed")
    with pytest.raises(RuntimeError):
        BigQueryWriter(client=c).write_season(REF, _df(), season=2025)
    assert not any("DELETE" in sql for sql in _sql(c))


def test_load_targets_staging_not_the_live_table():
    c = _client()
    BigQueryWriter(client=c).write_season(REF, _df(), season=2025)
    destination = str(c.load_table_from_dataframe.call_args.args[1])
    assert destination != TARGET
    assert "_staging_" in destination


def test_delete_and_insert_commit_in_one_transaction():
    c = _client()
    n = BigQueryWriter(client=c).write_season(REF, _df(), season=2025)
    assert n == 2
    swaps = [sql for sql in _sql(c) if "DELETE" in sql]
    assert len(swaps) == 1
    sql = swaps[0]
    assert sql.lstrip().startswith("BEGIN TRANSACTION")
    assert sql.rstrip().endswith("COMMIT TRANSACTION;")
    assert f"DELETE FROM `{TARGET}` WHERE season = @season" in sql
    assert sql.index("DELETE") < sql.index("INSERT INTO")
    staging = str(c.load_table_from_dataframe.call_args.args[1])
    assert f"FROM `{staging}`" in sql
    params = c.query_and_wait.call_args.kwargs["job_config"].query_parameters
    assert params[0].name == "season" and params[0].value == 2025


def test_staging_table_dropped_even_when_swap_fails():
    c = _client()
    c.query_and_wait.side_effect = RuntimeError("transaction aborted")
    with pytest.raises(RuntimeError):
        BigQueryWriter(client=c).write_season(REF, _df(), season=2025)
    staging = str(c.load_table_from_dataframe.call_args.args[1])
    assert staging in [str(call.args[0]) for call in c.delete_table.call_args_list]


def test_staging_load_uses_the_live_table_schema_and_coerces():
    c = _client()
    BigQueryWriter(client=c).write_season(
        REF, pd.DataFrame({"season": [2025.0], "play_id": [7.0]}), season=2025,
    )
    jc = c.load_table_from_dataframe.call_args.kwargs["job_config"]
    assert [f.name for f in jc.schema] == ["season", "play_id"]
    loaded = c.load_table_from_dataframe.call_args.args[0]
    assert str(loaded["play_id"].dtype) == "Int64"
