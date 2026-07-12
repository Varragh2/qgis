"""Command-line entry point for the GPS road-completion pipeline."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from constants import PROJECT_FILE, configure_logging
from qgis_runtime import initialize_qgis

LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Run every pipeline stage headlessly and stream each stage's log output."""
    configure_logging()
    app = None
    processing = None
    try:
        app, processing = initialize_qgis()
        from qgis.core import QgsProject
        from calculate_roads_completed import main as calculate_roads_completed
        from download_gps import main as download_gps
        from load_temporal_gpx_data import main as load_temporal_gpx_data

        project = QgsProject.instance()
        if not PROJECT_FILE.is_file():
            raise FileNotFoundError(f"QGIS project not found: {PROJECT_FILE}")
        if not project.read(str(PROJECT_FILE)):
            raise RuntimeError(f"Unable to read QGIS project: {PROJECT_FILE}")

        LOGGER.info("Running download_gps")
        download_gps()
        LOGGER.info("Running load_temporal_gpx_data")
        load_temporal_gpx_data(project)
        LOGGER.info("Running calculate_roads_completed")
        calculate_roads_completed(project)
        LOGGER.info("Pipeline completed successfully.")
    finally:
        if processing is not None:
            processing.deinitialize()
        if app is not None:
            app.exitQgis()


if __name__ == "__main__":
    main()
