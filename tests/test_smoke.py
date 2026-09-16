import subprocess
import sys
import tomllib
from pathlib import Path

import nfl_bigquery


def test_version_exported_matches_the_packaged_version():
    """nfl_bigquery/_version.py and pyproject.toml must stay pinned to each
    other -- a hardcoded literal here drifts silently the next time either
    file is bumped alone (mirrors ffl-bigquery's
    test_the_packaged_version_and_the_reported_version_agree)."""
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    packaged = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["version"]
    assert nfl_bigquery.__version__ == packaged, (
        f"nfl_bigquery.__version__ says {nfl_bigquery.__version__} but "
        f"pyproject.toml says {packaged}"
    )


def test_cli_version_runs():
    out = subprocess.run(
        [sys.executable, "-m", "nfl_bigquery.cli", "--version"],
        capture_output=True, text=True,
    )
    assert out.returncode == 0
    assert nfl_bigquery.__version__ in out.stdout
