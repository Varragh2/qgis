import os

from gpx_geopackage_loader import import_gpx_directory
from qgis.core import QgsProject

# --- CONFIGURATION ---
GPX_FOLDER = os.path.expanduser("~/Documents/qgis/synthetic_data")
GPKG_PATH = os.path.expanduser("~/Documents/qgis/geopackages/gps_temporal_data.gpkg")
LAYER_NAME = "GPS_temporal_data"
TARGET_CRS = "EPSG:3857"
# ---------------------

result = import_gpx_directory(
    GPX_FOLDER,
    GPKG_PATH,
    LAYER_NAME,
    TARGET_CRS,
    QgsProject.instance(),
)

master_layer = QgsProject.instance().mapLayersByName(LAYER_NAME)
total = master_layer[0].featureCount() if master_layer else 0

print("=" * 30)
print("GPKG IMPORT SUMMARY")
print(f"File Path: {GPKG_PATH}")
print(f"New tracks added: {result.added}")
print(f"Duplicates skipped: {result.skipped}")
if result.errors:
    print(f"Errors: {len(result.errors)}")
    for err in result.errors:
        print(f"  - {err}")
print(f"Total tracks in layer: {total}")
print("=" * 30)
