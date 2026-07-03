# nfl_bigquery/players/writer.py
"""dim_players upsert: stage table + MERGE on gsis_id, then drop stage.

The MERGE column lists are generated from DIM_PLAYERS_SCHEMA so the writer stays
faithful to the full player dimension without hardcoding ~30 columns.
"""
from __future__ import annotations

import logging
import uuid

import pandas as pd
from google.cloud import bigquery

from nfl_bigquery.schema import ColumnSpec, to_bq_schema
from nfl_bigquery.writer import coerce_df_for_bq

log = logging.getLogger(__name__)


def build_merge_sql(*, target: str, source: str, schema: list[ColumnSpec], key: str) -> str:
    cols = [s.name for s in schema]
    non_key = [c for c in cols if c != key]
    set_clause = ",\n  ".join(f"{c} = s.{c}" for c in non_key)
    insert_cols = ", ".join(cols)
    insert_vals = ", ".join(f"s.{c}" for c in cols)
    return (
        f"MERGE `{target}` t\n"
        f"USING `{source}` s\n"
        f"ON t.{key} = s.{key}\n"
        f"WHEN MATCHED THEN UPDATE SET\n  {set_clause}\n"
        f"WHEN NOT MATCHED THEN INSERT ({insert_cols})\n"
        f"VALUES ({insert_vals})"
    ).strip()


def upsert_players(
    client: bigquery.Client, *, target: str, df: pd.DataFrame,
    schema: list[ColumnSpec], key: str = "gsis_id",
) -> int:
    if df.empty:
        log.info("upsert_players: empty df, skipping")
        return 0
    proj, ds, _ = target.split(".")
    stage = f"{proj}.{ds}._dim_players_stage_{uuid.uuid4().hex[:8]}"
    bq_schema = to_bq_schema(schema)
    df = coerce_df_for_bq(df, bq_schema)
    client.load_table_from_dataframe(
        df, stage,
        job_config=bigquery.LoadJobConfig(
            schema=bq_schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        ),
    ).result()
    log.info("staged %d rows in %s", len(df), stage)
    try:
        client.query(build_merge_sql(target=target, source=stage, schema=schema, key=key)).result()
    finally:
        client.query(f"DROP TABLE `{stage}`").result()
    log.info("merged + dropped stage for %s", target)
    return len(df)
