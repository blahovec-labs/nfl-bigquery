"""Vendor nflverse data-dictionary snapshots as CSV (field,description,type).

Primary source: nflreadr `data-raw` CSVs on GitHub for field names and
descriptions.  The `type` column is derived from actual nflverse column dtypes
loaded via nflreadpy — not from the dictionary CSV's own type column, which is
absent for some tables and unreliable for others.

Run: `python scripts/refresh_dictionaries.py`.
"""
from __future__ import annotations

import io
import platform
import subprocess
from pathlib import Path

import nflreadpy as nfl
import pandas as pd
import polars as pl
import requests
from _norton_ssl import patch_nflreadpy_session_if_windows

OUT = Path("nfl_bigquery/dictionaries")
BASE = "https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw"
SOURCES = {
    "pbp": f"{BASE}/dictionary_pbp.csv",
    "schedules": f"{BASE}/dictionary_schedules.csv",
    "players": f"{BASE}/dictionary_players.csv",
    "player_stats": f"{BASE}/dictionary_playerstats.csv",
}

# nflreadr dictionaries name columns variously; normalize by recognizing these aliases.
_FIELD_NAMES: set[str] = {"field", "variable", "name"}
_DESC_NAMES: set[str] = {"description", "definition"}
_TYPE_NAMES: set[str] = {"type", "data_type"}

# The complete set of valid type tokens in the vendored CSVs.
_VALID_TOKENS: frozenset[str] = frozenset(
    {"numeric", "character", "integer", "logical", "date", "timestamp"}
)


def _fetch(url: str) -> str:
    """Download URL text.

    On Windows, uses the system curl.exe (Schannel TLS) with --ssl-no-revoke so
    that Norton Antivirus MITM CA certs are accepted via the Windows trust store.
    Certificate chain verification remains ON; only the CRL/OCSP revocation check
    is skipped.  On non-Windows, falls back to the requests library.
    """
    if platform.system() == "Windows":
        result = subprocess.run(
            ["curl.exe", "--ssl-no-revoke", "-s", "--fail", url],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        return result.stdout
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def _polars_type_token(dtype: pl.DataType) -> str:
    """Map a polars DataType to one of the valid dictionary type tokens."""
    if dtype.is_integer():
        return "integer"
    if dtype.is_float():
        return "numeric"
    if isinstance(dtype, pl.Boolean):
        return "logical"
    if isinstance(dtype, pl.Date):
        return "date"
    if isinstance(dtype, pl.Datetime):
        return "timestamp"
    # String, Categorical, Enum, Null, and any other type -> character
    return "character"


def _build_type_map(df: pl.DataFrame) -> dict[str, str]:
    """Return {column_name: type_token} derived from a polars DataFrame's schema."""
    return {col: _polars_type_token(dtype) for col, dtype in df.schema.items()}


def _normalize(
    df: pd.DataFrame,
    type_map: dict[str, str],
) -> pd.DataFrame:
    """Normalize a raw dictionary CSV into the canonical field,description,type shape."""
    str_cols = [str(c) for c in df.columns]
    cols_lower = {c.lower(): c for c in str_cols}

    def pick(names: set[str], default: str) -> str:
        for a in names:
            if a in cols_lower:
                return cols_lower[a]
        return default

    field_c = pick(_FIELD_NAMES, str_cols[0])
    desc_c = pick(_DESC_NAMES, str_cols[1])
    orig_type_c = pick(_TYPE_NAMES, str_cols[-1])

    fields = df[field_c].astype(str).str.strip()
    descs = df[desc_c].astype(str).str.strip()
    orig_types = df[orig_type_c].astype(str).str.strip().str.lower()

    def resolve_type(field: str, orig: str) -> str:
        # Authoritative: dtype derived from real nflverse data.
        if field in type_map:
            return type_map[field]
        # Fallback: use the dictionary's own type only when it's already a valid token.
        if orig in _VALID_TOKENS:
            return orig
        return "character"

    types = [resolve_type(f, o) for f, o in zip(fields, orig_types)]

    out = pd.DataFrame({"field": fields, "description": descs, "type": types})
    # Drop rows with empty or NaN-derived ("nan") field names.
    mask = (out["field"] != "") & (out["field"] != "nan")
    return out[mask].reset_index(drop=True)  # type: ignore[return-value]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    patch_nflreadpy_session_if_windows()

    print("Loading nflverse data to derive column types...")
    type_maps: dict[str, dict[str, str]] = {
        "pbp": _build_type_map(nfl.load_pbp([2023])),
        "schedules": _build_type_map(nfl.load_schedules([2023])),
        "players": _build_type_map(nfl.load_players()),
        "player_stats": _build_type_map(nfl.load_player_stats([2023])),
    }

    for name, url in SOURCES.items():
        text = _fetch(url)
        df = _normalize(pd.read_csv(io.StringIO(text)), type_maps[name])
        df.to_csv(OUT / f"{name}.csv", index=False)
        print(f"wrote {name}.csv ({len(df)} rows)")


if __name__ == "__main__":
    main()
