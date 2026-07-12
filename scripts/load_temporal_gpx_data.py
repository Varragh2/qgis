"""Import the project's collected GPX tracks into the temporal GeoPackage."""

from __future__ import annotations

import logging

from constants import GPS_GPKG_PATH, GPS_LAYER_NAME, REAL_DATA_DIR, TARGET_CRS
from gpx_geopackage_loader import ImportResult, import_gpx_directory
from qgis.core import QgsProject

LOGGER = logging.getLogger(__name__)


def main(project: QgsProject | None = None) -> ImportResult:
    project = project or QgsProject.instance()
    result = import_gpx_directory(
        str(REAL_DATA_DIR),
        str(GPS_GPKG_PATH),
        GPS_LAYER_NAME,
        TARGET_CRS,
        project,
    )

    master_layer = project.mapLayersByName(GPS_LAYER_NAME)
    total = master_layer[0].featureCount() if master_layer else 0
    LOGGER.info("GPKG IMPORT SUMMARY")
    LOGGER.info("File Path: %s", GPS_GPKG_PATH)
    LOGGER.info("New tracks added: %s", result.added)
    LOGGER.info("Duplicates skipped: %s", result.skipped)
    if result.errors:
        LOGGER.error("Errors: %s", len(result.errors))
        for error in result.errors:
            LOGGER.error("  - %s", error)
    LOGGER.info("Total tracks in layer: %s", total)
    return result


if __name__ == "__main__":
    main()
