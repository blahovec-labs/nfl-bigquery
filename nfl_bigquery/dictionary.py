"""Build ColumnSpec lists by seeding from a vendored nflverse dictionary CSV
and merging a hand enrichment overlay.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from nfl_bigquery.schema import ColumnSpec

_DEFAULT_DICT_DIR = Path(__file__).parent / "dictionaries"

_TYPE_MAP = {
    "character": "STRING", "string": "STRING", "factor": "STRING",
    "numeric": "FLOAT64", "double": "FLOAT64", "real": "FLOAT64", "float": "FLOAT64",
    "integer": "INT64", "int": "INT64",
    "logical": "BOOL", "boolean": "BOOL", "bool": "BOOL",
    "date": "DATE",
    "datetime": "TIMESTAMP", "timestamp": "TIMESTAMP",
}


def map_bq_type(dict_type: str, name: str, overrides: dict[str, str]) -> str:
    if name in overrides:
        return overrides[name]
    key = (dict_type or "").strip().lower()
    if key not in _TYPE_MAP:
        raise ValueError(f"{name}: unmapped dictionary type {dict_type!r}")
    return _TYPE_MAP[key]


def load_dictionary(table: str, dict_dir: str | Path = _DEFAULT_DICT_DIR) -> pd.DataFrame:
    path = Path(dict_dir) / f"{table}.csv"
    df = pd.read_csv(path)
    return df


def build_specs(
    table: str,
    *,
    dict_dir: str | Path = _DEFAULT_DICT_DIR,
    enrichment: dict[str, dict] | None = None,
    type_overrides: dict[str, str] | None = None,
) -> list[ColumnSpec]:
    """Seed ColumnSpecs from the dictionary CSV, then merge the enrichment overlay."""
    enrichment = enrichment or {}
    type_overrides = type_overrides or {}
    df = load_dictionary(table, dict_dir)
    specs: list[ColumnSpec] = []
    for _, row in df.iterrows():
        name = str(row["field"]).strip()
        desc = str(row["description"]).strip()
        if not desc or desc.lower() == "nan":
            desc = f"nflverse `{name}` column (no dictionary description)."
        over = enrichment.get(name, {})
        specs.append(ColumnSpec(
            name=name,
            type=over.get("type", map_bq_type(str(row["type"]), name, type_overrides)),
            mode=over.get("mode", "NULLABLE"),
            short_description=over.get("short_description", desc)[:1024],
            business_definition=over.get("business_definition", desc),
            semantic_tags=over.get("semantic_tags", []),
            valid_range=over.get("valid_range"),
            valid_values=over.get("valid_values"),
            example_value=over.get("example_value"),
            gotchas=over.get("gotchas", []),
            source_field=name,
            dictionary_type=str(row["type"]).strip(),
            deprecated_in_year=over.get("deprecated_in_year"),
        ))
    return specs
