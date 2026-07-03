# nfl_bigquery/writer.py
"""TableRef + BigQueryWriter: season-scoped idempotent writes.

Fact tables are keyed on the INT64 `season` column: DELETE WHERE season=@s, then
PARQUET load (WRITE_APPEND). create_table_if_missing dispatches on the partition
descriptor (DAY time-partition vs integer RANGE(season) vs none).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from nfl_bigquery.partition import SeasonRangePartition, TimePartition

log = logging.getLogger(__name__)

Partition = TimePartition | SeasonRangePartition | None


def coerce_df_for_bq(df: pd.DataFrame, schema: list[bigquery.SchemaField]) -> pd.DataFrame:
    df = df.copy()
    by_name = {f.name: f for f in schema}
    for col in df.columns:
        field = by_name.get(col)
        if field is None:
            continue
        ft = field.field_type.upper()
        if ft == "DATE" and df[col].dtype == object:
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.date
        elif ft in ("TIMESTAMP", "DATETIME") and df[col].dtype == object:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
        elif ft == "BOOL" and df[col].dtype == object:
            df[col] = df[col].astype("boolean")
        elif ft in ("INT64", "INTEGER"):
            # Cast INT64-typed columns regardless of source dtype: nflverse stores
            # many integers as float64 (they carry NA), but our schema declares INT64
            # for clean ids/filters, and RANGE(season) partitioning REQUIRES an INT64
            # column. "Int64" is pandas' nullable integer, so NA survives the cast.
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")  # type: ignore[union-attr]
        elif ft in ("FLOAT64", "FLOAT", "NUMERIC") and df[col].dtype == object:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@dataclass(frozen=True)
class TableRef:
    project: str
    dataset: str
    table: str

    def __str__(self) -> str:
        return f"{self.project}.{self.dataset}.{self.table}"

    @classmethod
    def parse(cls, s: str) -> TableRef:
        parts = s.split(".")
        if len(parts) != 3:
            raise ValueError(f"expected project.dataset.table, got {s!r}")
        return cls(*parts)


class BigQueryWriter:
    def __init__(self, client: bigquery.Client | None = None) -> None:
        self.client = client or bigquery.Client()

    def create_table_if_missing(
        self, ref: TableRef, schema: list[bigquery.SchemaField], partition: Partition = None,
    ) -> None:
        try:
            self.client.get_table(str(ref))
            return
        except NotFound:
            pass
        table = bigquery.Table(str(ref), schema=schema)
        if isinstance(partition, TimePartition):
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY, field=partition.field,
            )
            table.clustering_fields = partition.clustering or None
        elif isinstance(partition, SeasonRangePartition):
            table.range_partitioning = bigquery.RangePartitioning(
                field=partition.field,
                range_=bigquery.PartitionRange(
                    start=partition.start, end=partition.end, interval=partition.interval,
                ),
            )
            table.clustering_fields = partition.clustering or None
        self.client.create_table(table)
        log.info("created table %s", ref)

    def write_season(self, ref: TableRef, df: pd.DataFrame, *, season: int) -> int:
        """DELETE rows for `season`, then INSERT df. Returns rows inserted."""
        if df.empty:
            log.info("write_season: empty df for %s season=%s", ref, season)
            return 0
        try:
            bq_schema = list(self.client.get_table(str(ref)).schema)
        except NotFound:
            bq_schema = []
        self.client.query(
            f"DELETE FROM `{ref}` WHERE season = @season",
            job_config=bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("season", "INT64", season)],
            ),
        ).result()
        if bq_schema:
            df = coerce_df_for_bq(df, bq_schema)
        self.client.load_table_from_dataframe(
            df, str(ref),
            job_config=bigquery.LoadJobConfig(
                write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
                schema=bq_schema or None,
            ),
        ).result()
        log.info("wrote %d rows to %s season=%s", len(df), ref, season)
        return len(df)
