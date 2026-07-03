import subprocess
import sys

import nfl_bigquery


def test_version_exported():
    assert nfl_bigquery.__version__ == "0.1.0"


def test_cli_version_runs():
    out = subprocess.run(
        [sys.executable, "-m", "nfl_bigquery.cli", "--version"],
        capture_output=True, text=True,
    )
    assert out.returncode == 0
    assert "0.1.0" in out.stdout
