# Changelog

## 0.1.1 — 2026-09-15
- `sync`: drop null-`player_id` rows from `weekly_player_stats` before load. nflverse weekly
  stats carry team-aggregate rows without a player from 2001 on; with `player_id` REQUIRED
  they made every season ≥ 2001 fail at load (`Required field player_id cannot be null`)
  while `nfl_plays` + `games` still landed. `player_id` stays REQUIRED.

## 0.1.0
- `sync`: season-chunked idempotent load of `nfl_plays` (372-col nflfastR pbp), `games`
  (schedules), `weekly_player_stats`; `--resume` via `_nfl_ingest_runs`.
- `players`: `dim_players` MERGE upsert on `gsis_id`.
- `docs`: llm / bq-apply / markdown / dictionary / dbt renderers from dictionary-seeded
  ColumnSpecs + enrichment overlay.
- `verify`: internal consistency + plays→weekly reconciliation for passing/rushing/receiving
  yards and TDs (6 metrics, 8 checks total).
- Schema-drift guard test against nflverse fixtures.
