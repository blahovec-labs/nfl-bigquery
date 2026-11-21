# Changelog

## 0.1.4 — 2026-11-21
- `sync` now exits 1 when any season failed (a load error or a shrink-guard refusal); the
  other seasons still run. Before, it always exited 0, so a failed season was visible only in
  `_nfl_ingest_runs` and the job never alerted.

## 0.1.3 — 2026-11-21
- A shrink guard on every replace. Atomic writes stop a failed load from wiping data, but not a load that succeeds with a short frame (an upstream outage that returns half the slice, or nothing). Before swapping, the writer now counts the rows already in the slice and raises `ShrinkGuardError`, deleting nothing, if the new frame is under 50% of them. Slices under 100 rows are exempt. Set `BIGQUERY_ALLOW_SHRINK=1` for a run where the source really did shrink. Every replace also logs `existing -> incoming` row counts.

## 0.1.2 — 2026-11-21
- `sync`: season writes are now atomic. `write_season` ran `DELETE ... WHERE season = @season`
  as its own query, then a separate load job; a load job can't join a transaction, so a failed
  load left the whole season of `nfl_plays`, `games` or `weekly_player_stats` deleted until the
  next good run (the failure that wiped 2026-06-02 from statcast-bigquery). It now loads into a
  short-lived `_staging_*` table (6-hour expiry backstop), then `DELETE` + `INSERT ... SELECT` in
  one multi-statement transaction, then drops the staging table. A failed load deletes nothing;
  a failed swap rolls back. Idempotency and the empty-frame no-op are unchanged.

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
