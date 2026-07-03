# tests/test_players_writer.py
from typing import cast
from unittest.mock import MagicMock

import pandas as pd
from google.cloud import bigquery

from nfl_bigquery.players.writer import build_merge_sql, upsert_players
from nfl_bigquery.schema import BqMode, BqType, ColumnSpec, to_bq_schema


def _spec(name: str, mode: str = "NULLABLE", type: str = "STRING") -> ColumnSpec:
    return ColumnSpec(name=name, type=cast(BqType, type), mode=cast(BqMode, mode),
                      short_description="x", business_definition="x", semantic_tags=[],
                      valid_range=None, valid_values=None, example_value=None, gotchas=[],
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


def test_upsert_players_coerces_float64_int64_and_pins_schema():
    """FLOAT64 columns that are INT64 in the schema must be coerced before staging.

    This is the bug that caused `dim_players` MERGE to fail on real nflverse data:
    nflverse returns height/weight/draft_year/draft_round/draft_pick as float64,
    but DIM_PLAYERS_SCHEMA declares them INT64. Without coercion the stage table
    auto-detects FLOAT64, and BigQuery refuses to MERGE FLOAT64 → INT64.
    """
    c = MagicMock(spec=bigquery.Client)
    schema = [
        _spec("gsis_id", "REQUIRED"),
        _spec("height", type="INT64"),
    ]
    # height arrives from nflverse as float64 (NA-capable)
    df = pd.DataFrame({"gsis_id": ["00-1"], "height": [72.0]})
    assert df["height"].dtype == float  # confirm precondition: source is float64

    upsert_players(c, target="p.d.dim_players", df=df, schema=schema)

    # Verify the df handed to load_table_from_dataframe has been coerced to Int64
    call = c.load_table_from_dataframe.call_args
    loaded_df: pd.DataFrame = call.args[0]
    assert loaded_df["height"].dtype.name == "Int64", (
        f"expected Int64, got {loaded_df['height'].dtype}"
    )

    # Verify the job_config carries an explicit schema matching to_bq_schema(schema)
    job_config: bigquery.LoadJobConfig = call.kwargs["job_config"]
    expected_bq_schema = to_bq_schema(schema)
    actual_schema = job_config.schema
    assert actual_schema is not None, "job_config.schema must not be None"
    assert len(actual_schema) == len(expected_bq_schema), (
        f"schema length mismatch: {len(actual_schema)} vs {len(expected_bq_schema)}"
    )
    for actual, expected in zip(actual_schema, expected_bq_schema):
        assert actual.name == expected.name
        assert actual.field_type == expected.field_type
