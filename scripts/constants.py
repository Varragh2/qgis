"""Centralized, environment-backed configuration for the GPS pipeline.

Set any of the variables below before running ``python scripts/main.py``.
Paths may use ``~``.  Defaults keep the project portable by resolving from the
repository root instead of a particular user's home directory.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


def _path(name: str, default: Path | str) -> Path:
    return Path(os.environ.get(name, str(default))).expanduser().resolve()


def _integer(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def _number(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


# Every environment variable read by the active pipeline is documented here.
ENVIRONMENT_VARIABLES = {
    "QGIS_PROJECT_ROOT": "Repository root containing data, styles, and the QGIS project.",
    "QGIS_PROJECT_FILE": "QGIS project to load before running the pipeline.",
    "QGIS_PREFIX_PATH": "QGIS installation's Contents/MacOS directory.",
    "PYTHONHOME": "QGIS Python framework directory (set automatically by main when needed).",
    "QT_QPA_PLATFORM": "Qt platform; main defaults this to offscreen for headless runs.",
    "PROJ_DATA": "PROJ data directory (set automatically by main when needed).",
    "GDAL_DATA": "GDAL data directory (set automatically by main when needed).",
    "GPX_UPLOAD_DIR": "Folder where newly uploaded GPX files are collected.",
    "REAL_DATA_DIR": "Destination folder for imported GPX files.",
    "GPS_GPKG_PATH": "GeoPackage that stores temporal GPS tracks.",
    "GPS_LAYER_NAME": "Temporal GPS layer name.",
    "TARGET_CRS": "CRS used by the GPS and road-completion outputs.",
    "ROAD_LAYER_NAME": "Road layer name in the QGIS project or road GeoPackage.",
    "ROAD_GPKG_PATH": "Fallback GeoPackage containing the road layer.",
    "WALKED_GPKG_PATH": "GeoPackage for walked-road segments.",
    "CHECKLIST_GPKG_PATH": "GeoPackage for the road-completion checklist.",
    "WALKED_LAYER_NAME": "Walked-road output layer name.",
    "CHECKLIST_LAYER_NAME": "Checklist output layer name.",
    "ROADS_COMPLETION_GROUP": "QGIS layer-tree group for styled outputs.",
    "ROADS_COMPLETION_STYLE": "QML style applied to road-completion outputs.",
    "GPS_BUFFER_DISTANCE": "GPS buffer distance in map units.",
    "COMPLETION_THRESHOLD": "Percentage at which a road is marked complete.",
    "LOG_LEVEL": "Python logging level, for example INFO or DEBUG.",
}

_DEFAULT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = _path("QGIS_PROJECT_ROOT", _DEFAULT_ROOT)
PROJECT_FILE = _path("QGIS_PROJECT_FILE", PROJECT_ROOT / "walk-all-sf-roads.qgz")

UPLOAD_SOURCE_DIR = _path(
    "GPX_UPLOAD_DIR", "~/Library/Mobile Documents/com~apple~CloudDocs/GPX"
)
REAL_DATA_DIR = _path("REAL_DATA_DIR", PROJECT_ROOT / "real_data")
GPS_GPKG_PATH = _path("GPS_GPKG_PATH", PROJECT_ROOT / "geopackages/gps_temporal_data.gpkg")
GPS_LAYER_NAME = os.environ.get("GPS_LAYER_NAME", "GPS_temporal_data")
TARGET_CRS = os.environ.get("TARGET_CRS", "EPSG:3857")

ROAD_LAYER_NAME = os.environ.get("ROAD_LAYER_NAME", "sf_roads")
ROAD_GPKG_PATH = _path("ROAD_GPKG_PATH", PROJECT_ROOT / "geopackages/sf-roads.gpkg")
WALKED_GPKG_PATH = _path("WALKED_GPKG_PATH", PROJECT_ROOT / "geopackages/walked_roads.gpkg")
CHECKLIST_GPKG_PATH = _path("CHECKLIST_GPKG_PATH", PROJECT_ROOT / "geopackages/roads_checklist.gpkg")
WALKED_LAYER_NAME = os.environ.get("WALKED_LAYER_NAME", "Temporal Overlap with gps")
CHECKLIST_LAYER_NAME = os.environ.get(
    "CHECKLIST_LAYER_NAME", "Temporal Roads Completed Checklist"
)
ROADS_COMPLETION_GROUP = os.environ.get("ROADS_COMPLETION_GROUP", "Roads Completion")
ROADS_COMPLETION_STYLE = _path("ROADS_COMPLETION_STYLE", PROJECT_ROOT / "styles/walked.qml")
GPS_BUFFER_DISTANCE = _number("GPS_BUFFER_DISTANCE", 15)
COMPLETION_THRESHOLD = _integer("COMPLETION_THRESHOLD", 70)
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()


def configure_logging() -> None:
    """Configure one console logger for command-line and QGIS runs."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
        force=True,
    )
