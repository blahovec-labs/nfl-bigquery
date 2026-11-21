# nfl_bigquery/writer.py
"""TableRef + BigQueryWriter: season-scoped idempotent writes.

Fact tables are keyed on the INT64 `season` column: stage the season, then
DELETE WHERE season=@s + INSERT in one transaction. create_table_if_missing
dispatches on the partition descriptor (DAY time-partition vs integer
RANGE(season) vs none).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from nfl_bigquery._atomic import atomic_replace
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
        """Replace the rows for `season` with df, atomically. Returns rows written.

        Stages df, then DELETE + INSERT in one transaction (see _atomic.py), so a
        failed load leaves the season's existing rows untouched. An empty df is a
        no-op: nothing is deleted. The table must exist (`run_sync` creates it).
        """
        if df.empty:
            log.info("write_season: empty df for %s season=%s", ref, season)
            return 0
        bq_schema = list(self.client.get_table(str(ref)).schema)
        n = atomic_replace(
            self.client, str(ref), coerce_df_for_bq(df, bq_schema), bq_schema,
            "season = @season",
            [bigquery.ScalarQueryParameter("season", "INT64", season)],
        )
        log.info("wrote %d rows to %s season=%s", n, ref, season)
        return n
