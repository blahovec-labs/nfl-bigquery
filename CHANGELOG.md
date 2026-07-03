# Changelog

## 0.1.0
- `sync`: season-chunked idempotent load of `nfl_plays` (372-col nflfastR pbp), `games`
  (schedules), `weekly_player_stats`; `--resume` via `_nfl_ingest_runs`.
- `players`: `dim_players` MERGE upsert on `gsis_id`.
- `docs`: llm / bq-apply / markdown / dictionary / dbt renderers from dictionary-seeded
  ColumnSpecs + enrichment overlay.
- `verify`: internal consistency + plays→weekly passing-yards reconciliation.
- Schema-drift guard test against nflverse fixtures.
