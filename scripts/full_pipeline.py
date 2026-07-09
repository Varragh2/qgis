"""One-button entrypoint for the GPS road-completion pipeline."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def run_script(script_name: str) -> None:
    print(f"\n>>> Running {script_name}")
    runpy.run_path(str(SCRIPT_DIR / script_name), run_name="__main__")


def main() -> None:
    for script_name in (
        "download_gps.py",
        "load_temporal_gpx_data.py",
        "calculate_roads_completed.py",
    ):
        run_script(script_name)


if __name__ == "__main__":
    main()
