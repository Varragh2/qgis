import os

from qgis.core import QgsProject
from roads_completion import RoadsCompletionConfig, run_roads_completion

# --- CONFIGURATION ---
ROAD_LAYER_NAME = "sf_roads"
GPS_LAYER_NAME = "GPS_temporal_data"
BUFFER_DIST = 15
COMPLETION_THRESHOLD = 70
WALKED_LAYER = "Temporal Overlap with gps"
CHECKLIST_LAYER = "Temporal Roads Completed Checklist"
WALKED_GPKG = os.path.expanduser("~/Documents/qgis/geopackages/walked_roads.gpkg")
CHECKLIST_GPKG = os.path.expanduser("~/Documents/qgis/geopackages/roads_checklist.gpkg")
TARGET_CRS = "EPSG:3857"
# ---------------------

project = QgsProject.instance()
road_layers = project.mapLayersByName(ROAD_LAYER_NAME)
gps_layers = project.mapLayersByName(GPS_LAYER_NAME)

if not road_layers or not gps_layers:
    raise RuntimeError(
        f"Load '{ROAD_LAYER_NAME}' and '{GPS_LAYER_NAME}' into the project before running."
    )

result = run_roads_completion(
    RoadsCompletionConfig(
        road_layer=road_layers[0],
        gps_layer=gps_layers[0],
        walked_gpkg_path=WALKED_GPKG,
        checklist_gpkg_path=CHECKLIST_GPKG,
        walked_layer_name=WALKED_LAYER,
        checklist_layer_name=CHECKLIST_LAYER,
        buffer_dist=BUFFER_DIST,
        completion_threshold=COMPLETION_THRESHOLD,
        crs=TARGET_CRS,
        project=project,
    )
)

print("=" * 30)
print("ROADS COMPLETION SUMMARY")
print(f"New filenames processed: {', '.join(result.added_filenames) or 'none'}")
print(f"Skipped filenames: {', '.join(result.skipped_filenames) or 'none'}")
print(f"Walked features added: {result.walked_features_added}")
print(f"Walked GPKG: {result.walked_gpkg_path}")
print(f"Checklist GPKG: {result.checklist_gpkg_path}")
if result.errors:
    for err in result.errors:
        print(f"  - {err}")
print("=" * 30)
