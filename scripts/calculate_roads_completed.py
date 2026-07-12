"""Calculate walked-road segments and refresh the completion checklist."""

from __future__ import annotations

import logging

from apply_style import apply_roads_completion_style
from constants import (
    CHECKLIST_GPKG_PATH,
    CHECKLIST_LAYER_NAME,
    COMPLETION_THRESHOLD,
    GPS_BUFFER_DISTANCE,
    GPS_LAYER_NAME,
    ROAD_GPKG_PATH,
    ROAD_LAYER_NAME,
    ROADS_COMPLETION_GROUP,
    ROADS_COMPLETION_STYLE,
    TARGET_CRS,
    WALKED_GPKG_PATH,
    WALKED_LAYER_NAME,
)
from qgis.core import QgsProject, QgsVectorLayer
from roads_completion import CompletionResult, RoadsCompletionConfig, run_roads_completion

LOGGER = logging.getLogger(__name__)

# Backwards-compatible names for users who ran this script directly in QGIS.
GROUP_NAME = ROADS_COMPLETION_GROUP
STYLE_QML = str(ROADS_COMPLETION_STYLE)


def _road_layer(project: QgsProject) -> QgsVectorLayer:
    layers = project.mapLayersByName(ROAD_LAYER_NAME)
    if layers:
        return layers[0]
    layer = QgsVectorLayer(
        f"{ROAD_GPKG_PATH}|layername={ROAD_LAYER_NAME}", ROAD_LAYER_NAME, "ogr"
    )
    if not layer.isValid():
        raise RuntimeError(
            f"Road layer '{ROAD_LAYER_NAME}' was not found in the project or {ROAD_GPKG_PATH}."
        )
    project.addMapLayer(layer)
    return layer


def main(project: QgsProject | None = None) -> CompletionResult:
    project = project or QgsProject.instance()
    road_layer = _road_layer(project)
    gps_layers = project.mapLayersByName(GPS_LAYER_NAME)
    if not gps_layers:
        raise RuntimeError(f"GPS layer '{GPS_LAYER_NAME}' was not loaded by the import step.")

    result = run_roads_completion(
        RoadsCompletionConfig(
            road_layer=road_layer,
            gps_layer=gps_layers[0],
            walked_gpkg_path=str(WALKED_GPKG_PATH),
            checklist_gpkg_path=str(CHECKLIST_GPKG_PATH),
            walked_layer_name=WALKED_LAYER_NAME,
            checklist_layer_name=CHECKLIST_LAYER_NAME,
            buffer_dist=GPS_BUFFER_DISTANCE,
            completion_threshold=COMPLETION_THRESHOLD,
            crs=TARGET_CRS,
            project=project,
            register_layers=False,
        )
    )
    apply_roads_completion_style(
        project=project,
        walked_gpkg_path=str(WALKED_GPKG_PATH),
        checklist_gpkg_path=str(CHECKLIST_GPKG_PATH),
        walked_layer_name=WALKED_LAYER_NAME,
        checklist_layer_name=CHECKLIST_LAYER_NAME,
        group_name=GROUP_NAME,
        style_qml_path=STYLE_QML,
    )

    LOGGER.info("ROADS COMPLETION SUMMARY")
    LOGGER.info("New filenames processed: %s", ", ".join(result.added_filenames) or "none")
    LOGGER.info("Skipped filenames: %s", ", ".join(result.skipped_filenames) or "none")
    LOGGER.info("Walked features added: %s", result.walked_features_added)
    LOGGER.info("Walked GPKG: %s", result.walked_gpkg_path)
    LOGGER.info("Checklist GPKG: %s", result.checklist_gpkg_path)
    for error in result.errors:
        LOGGER.error("  - %s", error)
    return result


if __name__ == "__main__":
    main()
