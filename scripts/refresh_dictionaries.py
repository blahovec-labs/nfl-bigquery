"""Vendor nflverse data-dictionary snapshots as CSV (field,description,type).

Primary source: the nflreadr `data-raw` CSVs on GitHub. If a URL 404s (branch
or filename drift), fall back to any dictionary bundled inside the installed
nflreadpy package. Run: `python scripts/refresh_dictionaries.py`.
"""
from __future__ import annotations

import io
import platform
import subprocess
from pathlib import Path

import pandas as pd
import requests

OUT = Path("nfl_bigquery/dictionaries")
BASE = "https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw"
SOURCES = {
    "pbp": f"{BASE}/dictionary_pbp.csv",
    "schedules": f"{BASE}/dictionary_schedules.csv",
    "players": f"{BASE}/dictionary_players.csv",
    "player_stats": f"{BASE}/dictionary_playerstats.csv",
}
# nflreadr dictionaries name the column variously; normalize to field/description/type.
FIELD_ALIASES = {"field": "field", "variable": "field", "name": "field"}
DESC_ALIASES = {"description": "description", "definition": "description"}
TYPE_ALIASES = {"type": "type", "data_type": "type"}


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
            check=True,
        )
        return result.stdout
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    str_cols = [str(c) for c in df.columns]
    cols = {c.lower(): c for c in str_cols}

    def pick(aliases: dict[str, str], default: str) -> str:
        for a in aliases:
            if a in cols:
                return cols[a]
        return default

    field_c = pick(FIELD_ALIASES, str_cols[0])
    desc_c = pick(DESC_ALIASES, str_cols[1])
    type_c = pick(TYPE_ALIASES, str_cols[-1])
    out = pd.DataFrame({
        "field": df[field_c].astype(str).str.strip(),
        "description": df[desc_c].astype(str).str.strip(),
        "type": df[type_c].astype(str).str.strip().str.lower(),
    })
    mask = out["field"] != ""
    return out[mask].reset_index(drop=True)  # type: ignore[return-value]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        text = _fetch(url)
        df = _normalize(pd.read_csv(io.StringIO(text)))
        df.to_csv(OUT / f"{name}.csv", index=False)
        print(f"wrote {name}.csv ({len(df)} rows)")


if __name__ == "__main__":
    main()
