"""nfl-bigquery CLI entrypoint."""
from __future__ import annotations

import argparse
import logging

from nfl_bigquery._version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nfl-bigquery")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")

    sy = sub.add_parser("sync", help="Fetch nflverse data and write to BigQuery")
    sy.add_argument("--seasons", required=True,
                    help="e.g. 1999-2025 | 2023,2025 | 2024 | latest")
    sy.add_argument("--pbp-table", required=True, help="project.dataset.nfl_plays")
    sy.add_argument("--games-table")
    sy.add_argument("--weekly-stats-table")
    sy.add_argument("--runs-table")
    sy.add_argument("--skip-games", action="store_true")
    sy.add_argument("--skip-weekly-stats", action="store_true")
    sy.add_argument("--resume", action="store_true")
    sy.add_argument("--dry-run", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = build_parser()
    ns = parser.parse_args(argv)
    if not getattr(ns, "command", None):
        parser.print_help()
        return 0
    if ns.command == "sync":
        from google.cloud import bigquery

        from nfl_bigquery.client import NflverseClient
        from nfl_bigquery.runs import RunsTable
        from nfl_bigquery.sync import run_sync
        from nfl_bigquery.writer import BigQueryWriter

        bq = bigquery.Client()
        return run_sync(ns, client=NflverseClient(), writer=BigQueryWriter(client=bq),
                        runs=RunsTable(client=bq))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
