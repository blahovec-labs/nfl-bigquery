# nfl-bigquery

NFL play-by-play → BigQuery. Idempotent nflverse ingestion + LLM-friendly docs + verification.
Fourth in the `*-bigquery` family (`statcast-bigquery`, `nhl-bigquery`, `yfinance-bigquery`).

## Install
```bash
pip install nfl-bigquery
gcloud auth application-default login
```

## Sync
```bash
# Backfill 1999–present into a shared dataset (idempotent, resumable)
nfl-bigquery sync --seasons 1999-2025 --resume \
    --pbp-table myproject.mydataset.nfl_plays
# Player dimension
nfl-bigquery players --players-table myproject.mydataset.dim_players
```

Writes `nfl_plays`, `games`, `weekly_player_stats` (season-chunked DELETE→INSERT) and
`dim_players` (MERGE on `gsis_id`), plus a `_nfl_ingest_runs` log for `--resume`.

## Docs & verify
```bash
nfl-bigquery docs --format llm
nfl-bigquery docs --format bq-apply --table myproject.mydataset.nfl_plays
nfl-bigquery verify --source internal --season 2024 \
    --pbp-table myproject.mydataset.nfl_plays
```

## Data source
All data from [nflverse](https://nflreadpy.nflverse.com/) via `nflreadpy`. Play-by-play is
nflfastR's 372-column feed (EPA/WPA/air-yards/CPOE modeled), back to 1999.

MIT licensed.
