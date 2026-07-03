"""players command: load the player dimension and MERGE-upsert on gsis_id."""
from __future__ import annotations

import argparse
import logging

from nfl_bigquery.players.schema import DIM_PLAYERS_KEY, DIM_PLAYERS_SCHEMA
from nfl_bigquery.players.transform import transform_players
from nfl_bigquery.players.writer import upsert_players
from nfl_bigquery.schema import to_bq_schema
from nfl_bigquery.writer import BigQueryWriter, TableRef

log = logging.getLogger(__name__)


def run_players(ns: argparse.Namespace, *, client, bq_client) -> int:
    ref = TableRef.parse(ns.players_table)
    if ns.dry_run:
        print(f"[dry-run] would upsert dim_players into {ref}")
        return 0
    BigQueryWriter(client=bq_client).create_table_if_missing(
        ref, to_bq_schema(DIM_PLAYERS_SCHEMA), None)
    df = transform_players(client.load_players())
    n = upsert_players(bq_client, target=str(ref), df=df,
                       schema=DIM_PLAYERS_SCHEMA, key=DIM_PLAYERS_KEY)
    log.info("dim_players upsert: %d rows", n)
    return 0
