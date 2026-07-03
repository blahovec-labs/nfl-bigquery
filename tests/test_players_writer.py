# tests/test_players_writer.py
from typing import cast
from unittest.mock import MagicMock

import pandas as pd
from google.cloud import bigquery

from nfl_bigquery.players.writer import build_merge_sql, upsert_players
from nfl_bigquery.schema import BqMode, ColumnSpec


def _spec(name: str, mode: str = "NULLABLE") -> ColumnSpec:
    return ColumnSpec(name=name, type="STRING", mode=cast(BqMode, mode), short_description="x",
                      business_definition="x", semantic_tags=[], valid_range=None,
                      valid_values=None, example_value=None, gotchas=[],
                      source_field=name, dictionary_type="character", deprecated_in_year=None)


def test_merge_sql_keys_on_gsis_id_and_skips_key_in_update():
    schema = [_spec("gsis_id", "REQUIRED"), _spec("display_name"), _spec("position")]
    sql = build_merge_sql(target="p.d.dim_players", source="p.d._stage",
                          schema=schema, key="gsis_id")
    assert "ON t.gsis_id = s.gsis_id" in sql
    assert "display_name = s.display_name" in sql
    assert "position = s.position" in sql
    # key column is not reassigned in the UPDATE SET clause
    assert "gsis_id = s.gsis_id" not in sql.split("WHEN NOT MATCHED")[0].split("UPDATE SET")[1]
    # key IS present in the INSERT half
    insert_part = sql.split("WHEN NOT MATCHED")[1]
    assert "gsis_id" in insert_part


def test_upsert_players_stages_merges_drops():
    c = MagicMock(spec=bigquery.Client)
    schema = [_spec("gsis_id", "REQUIRED"), _spec("display_name")]
    df = pd.DataFrame({"gsis_id": ["00-1"], "display_name": ["A B"]})
    n = upsert_players(c, target="p.d.dim_players", df=df, schema=schema)
    assert n == 1
    assert c.load_table_from_dataframe.called          # stage load
    merge_sql = c.query.call_args_list[0][0][0]
    assert "MERGE" in merge_sql
    drop_sql = c.query.call_args_list[1][0][0]
    assert "DROP TABLE" in drop_sql
    job_config = c.load_table_from_dataframe.call_args.kwargs["job_config"]
    assert job_config.write_disposition == bigquery.WriteDisposition.WRITE_TRUNCATE


def test_upsert_players_empty_df_returns_zero():
    c = MagicMock(spec=bigquery.Client)
    n = upsert_players(c, target="p.d.dim_players", df=pd.DataFrame(), schema=[], key="gsis_id")
    assert n == 0
    c.load_table_from_dataframe.assert_not_called()
    c.query.assert_not_called()
