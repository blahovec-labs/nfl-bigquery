"""Hand enrichment overlay for the highest-value nfl_plays columns.
Keys are column names; values override ColumnSpec fields (see dictionary.build_specs).
Columns absent here still get a complete, dictionary-seeded spec.

Type policy: base BQ types come from the vendored dictionary CSV's `type` column,
which is DATA-DERIVED from real nflverse dtypes (see scripts/refresh_dictionaries.py).
This overlay only overrides `type` where a correctness-critical, clean integer/date is
wanted (season/week/down/ydstogo -> INT64; game_date -> DATE via type_overrides). It does
NOT force BOOL on nflfastR's 0/1 numeric indicators.
"""
from __future__ import annotations

ENRICHMENT: dict[str, dict] = {
    # --- REQUIRED identifiers ---
    "game_id": {
        "mode": "REQUIRED",
        "semantic_tags": ["identifier", "join_key"],
        "example_value": "2023_01_DET_KC",
        "gotchas": ["nflverse string id; join `games.game_id`. Not the numeric old_game_id."],
    },
    "play_id": {
        "mode": "REQUIRED",
        "semantic_tags": ["identifier"],
        "example_value": 1.0,
        "gotchas": ["Unique only within a game; key on (game_id, play_id)."],
    },
    "season": {
        "mode": "REQUIRED", "type": "INT64",
        "semantic_tags": ["identifier", "partition_filter"],
        "valid_range": (1999.0, 2100.0), "example_value": 2023,
    },
    "week": {
        "mode": "REQUIRED", "type": "INT64",
        "semantic_tags": ["identifier", "cluster_key"],
        "valid_range": (1.0, 22.0), "example_value": 1,
    },
    "game_date": {
        "mode": "REQUIRED",
        "semantic_tags": ["identifier", "partition_key"],
        "example_value": "2023-09-07",
    },
    # --- team dimension ---
    "home_team": {"semantic_tags": ["dimension"]},
    "away_team": {"semantic_tags": ["dimension"]},
    # --- categorical with valid_values ---
    "play_type": {
        "semantic_tags": ["dimension"],
        "valid_values": ["pass", "run", "punt", "field_goal", "kickoff",
                          "extra_point", "qb_kneel", "qb_spike", "no_play"],
        "example_value": "pass",
        "gotchas": ["Null on timeouts/administrative rows."],
    },
    "posteam": {"semantic_tags": ["dimension", "cluster_key"], "example_value": "KC"},
    "defteam": {"semantic_tags": ["dimension"], "example_value": "DET"},
    # --- score situation ---
    "home_score": {"semantic_tags": ["situation"], "valid_range": (0.0, 80.0)},
    "away_score": {"semantic_tags": ["situation"], "valid_range": (0.0, 80.0)},
    "posteam_score": {"semantic_tags": ["situation"], "valid_range": (0.0, 80.0)},
    "defteam_score": {"semantic_tags": ["situation"], "valid_range": (0.0, 80.0)},
    # --- game state / situation ---
    "qtr": {"semantic_tags": ["situation"], "valid_range": (1.0, 6.0)},
    "drive": {"semantic_tags": ["situation"]},
    # --- bounded float metrics ---
    "epa": {
        "semantic_tags": ["metric", "modeled"], "valid_range": (-15.0, 15.0),
        "example_value": 0.42,
        "gotchas": ["Expected Points Added for the posteam. Null on no-play rows."],
    },
    "wpa": {
        "semantic_tags": ["metric", "modeled"], "valid_range": (-1.0, 1.0),
        "example_value": 0.03, "gotchas": ["Win Probability Added for the posteam."],
    },
    "air_yards": {
        "semantic_tags": ["metric"], "valid_range": (-20.0, 80.0), "example_value": 7.0,
        "gotchas": ["Distance ball traveled past LOS; null on non-pass plays."],
    },
    "yards_after_catch": {
        "semantic_tags": ["metric"], "valid_range": (0.0, 100.0), "example_value": 5.0,
    },
    "cpoe": {
        "semantic_tags": ["metric", "modeled"], "valid_range": (-100.0, 100.0),
        "example_value": 3.1, "gotchas": ["Completion % Over Expected; pass plays only."],
    },
    "wp": {
        "semantic_tags": ["metric", "modeled"], "valid_range": (0.0, 1.0),
        "example_value": 0.55, "gotchas": ["Pre-play posteam win probability."],
    },
    # --- EPA decomposition (air/YAC/QB) ---
    "air_epa": {"semantic_tags": ["metric", "modeled"], "valid_range": (-15.0, 15.0)},
    "yac_epa": {"semantic_tags": ["metric", "modeled"], "valid_range": (-15.0, 15.0)},
    "comp_air_epa": {"semantic_tags": ["metric", "modeled"], "valid_range": (-15.0, 15.0)},
    "comp_yac_epa": {"semantic_tags": ["metric", "modeled"], "valid_range": (-15.0, 15.0)},
    "qb_epa": {"semantic_tags": ["metric", "modeled"], "valid_range": (-15.0, 15.0)},
    "xyac_epa": {"semantic_tags": ["metric", "modeled"], "valid_range": (-15.0, 15.0)},
    # --- bounded counts ---
    "down": {"type": "INT64", "semantic_tags": ["dimension"], "valid_range": (1.0, 4.0)},
    "ydstogo": {"type": "INT64", "semantic_tags": ["situation"], "valid_range": (0.0, 99.0)},
    "yardline_100": {
        "semantic_tags": ["situation"], "valid_range": (0.0, 100.0), "example_value": 75.0,
        "gotchas": ["Yards from opponent end zone; 100 = own goal line."],
    },
    "yards_gained": {"semantic_tags": ["metric"], "valid_range": (-99.0, 99.0)},
    "score_differential": {"semantic_tags": ["situation"], "valid_range": (-59.0, 59.0)},
    "game_seconds_remaining": {"semantic_tags": ["situation"], "valid_range": (0.0, 3600.0)},
    "penalty_yards": {"semantic_tags": ["metric"], "valid_range": (0.0, 100.0)},
    "kick_distance": {"semantic_tags": ["metric"], "valid_range": (0.0, 80.0)},
    # --- 0/1 indicators (nflfastR stores these as numeric doubles; keep them
    #     data-derived FLOAT64 rather than forcing BOOL, which fights the source
    #     dtype and needs no coercion) ---
    "pass_touchdown": {"semantic_tags": ["outcome"]},
    "rush_touchdown": {"semantic_tags": ["outcome"]},
    "interception": {"semantic_tags": ["outcome"]},
    "fumble_lost": {"semantic_tags": ["outcome"]},
    "sack": {"semantic_tags": ["outcome"]},
    "success": {"semantic_tags": ["metric", "modeled"],
                "gotchas": ["1.0 if EPA > 0 for the posteam (nflfastR 0/1 double)."]},
    "first_down": {"semantic_tags": ["outcome"]},
    "third_down_converted": {"semantic_tags": ["outcome"]},
    "fourth_down_converted": {"semantic_tags": ["outcome"]},
    "touchdown": {"semantic_tags": ["outcome"]},
    "penalty": {"semantic_tags": ["outcome"]},
    # --- outcome with valid_values ---
    "field_goal_result": {
        "semantic_tags": ["outcome"],
        "valid_values": ["made", "missed", "blocked"],
    },
    # --- actor ids ---
    "passer_player_id": {
        "semantic_tags": ["identifier", "actor"],
        "gotchas": ["gsis_id; join dim_players.gsis_id."],
    },
    "rusher_player_id": {"semantic_tags": ["identifier", "actor"],
                          "gotchas": ["gsis_id; join dim_players.gsis_id."]},
    "receiver_player_id": {"semantic_tags": ["identifier", "actor"],
                            "gotchas": ["gsis_id; join dim_players.gsis_id."]},
    # --- actor names ---
    "passer_player_name": {
        "semantic_tags": ["actor"],
        "gotchas": ["Human-readable; join via the matching *_player_id (gsis_id)."],
    },
    "rusher_player_name": {
        "semantic_tags": ["actor"],
        "gotchas": ["Human-readable; join via the matching *_player_id (gsis_id)."],
    },
    "receiver_player_name": {
        "semantic_tags": ["actor"],
        "gotchas": ["Human-readable; join via the matching *_player_id (gsis_id)."],
    },
    # --- fantasy identifier ---
    "fantasy_player_id": {
        "semantic_tags": ["identifier", "actor"],
        "gotchas": ["gsis_id of the primary fantasy player on the play."],
    },
}
