# tests/test_writer.py
from unittest.mock import MagicMock

import pandas as pd
import pytest
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from nfl_bigquery.partition import SeasonRangePartition, TimePartition
from nfl_bigquery.writer import BigQueryWriter, TableRef


def _client():
    c = MagicMock(spec=bigquery.Client)
    c.project = "p"
    return c


def test_tableref_parse_roundtrip():
    assert str(TableRef.parse("p.d.nfl_plays")) == "p.d.nfl_plays"


def test_create_time_partition_when_missing():
    c = _client()
    c.get_table.side_effect = NotFound("missing")
    w = BigQueryWriter(client=c)
    schema = [bigquery.SchemaField("game_date", "DATE")]
    w.create_table_if_missing(TableRef.parse("p.d.nfl_plays"), schema,
                              TimePartition(field="game_date", clustering=["season"]))
    table = c.create_table.call_args[0][0]
    assert table.time_partitioning.field == "game_date"
    assert table.clustering_fields == ["season"]


def test_create_range_partition_when_missing():
    c = _client()
    c.get_table.side_effect = NotFound("missing")
    w = BigQueryWriter(client=c)
    schema = [bigquery.SchemaField("season", "INT64")]
    w.create_table_if_missing(TableRef.parse("p.d.weekly"), schema,
                              SeasonRangePartition(clustering=["week"]))
    table = c.create_table.call_args[0][0]
    assert table.range_partitioning.field == "season"
    assert table.range_partitioning.range_.start == 1999
    assert table.range_partitioning.range_.end == 2100
    assert table.range_partitioning.range_.interval == 1


def test_write_season_deletes_then_loads():
    c = _client()
    got = bigquery.Table("p.d.nfl_plays", schema=[bigquery.SchemaField("season", "INT64")])
    c.get_table.return_value = got
    w = BigQueryWriter(client=c)
    df = pd.DataFrame({"season": [2023, 2023]})
    n = w.write_season(TableRef.parse("p.d.nfl_plays"), df, season=2023)
    assert n == 2
    delete_sql = c.query.call_args[0][0]
    assert "DELETE FROM" in delete_sql and "season = @season" in delete_sql
    assert c.load_table_from_dataframe.called
    job_config = c.load_table_from_dataframe.call_args.kwargs["job_config"]
    assert job_config.write_disposition == bigquery.WriteDisposition.WRITE_APPEND


def test_write_season_empty_df_noop():
    c = _client()
    w = BigQueryWriter(client=c)
    n = w.write_season(TableRef.parse("p.d.x"), pd.DataFrame(), season=2023)
    assert n == 0
    assert not c.query.called


def test_tableref_parse_rejects_two_parts():
    with pytest.raises(ValueError):
        TableRef.parse("p.d")


def test_create_table_skips_when_exists():
    c = _client()
    c.get_table.return_value = bigquery.Table("p.d.nfl_plays")
    w = BigQueryWriter(client=c)
    schema = [bigquery.SchemaField("game_date", "DATE")]
    w.create_table_if_missing(TableRef.parse("p.d.nfl_plays"), schema)
    assert not c.create_table.called
