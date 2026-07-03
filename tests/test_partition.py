from nfl_bigquery.partition import SeasonRangePartition, TimePartition


def test_time_partition():
    p = TimePartition(field="game_date", clustering=["season", "week", "posteam"])
    assert p.field == "game_date"
    assert p.clustering == ["season", "week", "posteam"]


def test_season_range_defaults():
    p = SeasonRangePartition(clustering=["week", "player_id"])
    assert p.field == "season"
    assert p.start == 1999
    assert p.end == 2100
    assert p.interval == 1
    assert p.clustering == ["week", "player_id"]
