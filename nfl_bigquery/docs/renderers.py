"""Five documentation renderers over the ColumnSpec registry:
llm / bq-apply / markdown / dictionary / dbt.
"""
from __future__ import annotations

from nfl_bigquery.docs.taxonomy import TABLES, TableDoc


def render_llm(tables: dict[str, TableDoc]) -> str:
    lines: list[str] = ["# NFL BigQuery tables (nfl-bigquery)", ""]
    for t in tables.values():
        lines.append(f"## {t.name} — {t.description}")
        for c in t.columns:
            tags = f" [{', '.join(c.semantic_tags)}]" if c.semantic_tags else ""
            lines.append(f"- `{c.name}` ({c.type}){tags}: {c.short_description}")
            for g in c.gotchas:
                lines.append(f"    - gotcha: {g}")
        lines.append("")
    return "\n".join(lines)


def render_bq_apply(table_name: str, ref: str) -> list[tuple[str, str]]:
    t = TABLES[table_name]
    return [(c.name, c.short_description[:1024]) for c in t.columns]


def render_markdown(tables: dict[str, TableDoc]) -> str:
    lines: list[str] = ["# nfl-bigquery data reference", ""]
    for t in tables.values():
        lines += [
            f"## {t.name}",
            "",
            t.description,
            "",
            "| column | type | mode | description |",
            "|---|---|---|---|",
        ]
        for c in t.columns:
            lines.append(f"| {c.name} | {c.type} | {c.mode} | {c.short_description} |")
        lines.append("")
    return "\n".join(lines)


def render_dictionary_rows(tables: dict[str, TableDoc]) -> list[dict]:
    rows: list[dict] = []
    for t in tables.values():
        for c in t.columns:
            rows.append({
                "table_name": t.name,
                "column_name": c.name,
                "data_type": c.type,
                "mode": c.mode,
                "short_description": c.short_description,
                "business_definition": c.business_definition,
                "semantic_tags": ",".join(c.semantic_tags),
                "gotchas": " | ".join(c.gotchas),
            })
    return rows


def render_dbt(tables: dict[str, TableDoc]) -> str:
    lines: list[str] = ["version: 2", "models:"]
    for t in tables.values():
        lines += [
            f"  - name: {t.name}",
            f'    description: "{t.description}"',
            "    columns:",
        ]
        for c in t.columns:
            lines += [
                f"      - name: {c.name}",
                f'        description: "{c.short_description}"',
            ]
    return "\n".join(lines)
