"""nfl-bigquery CLI entrypoint."""
from __future__ import annotations

import argparse

from nfl_bigquery._version import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nfl-bigquery")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_subparsers(dest="command")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)
    if not getattr(ns, "command", None):
        parser.print_help()
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
