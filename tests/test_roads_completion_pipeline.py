"""Integration tests for the roads completion pipeline."""

import os

from qgis.core import QgsProject, QgsVectorLayer

from fixtures.roads_completion_layers import (
    OAK_ST,
    PINE_ST,
    WALK_OAK_EARLY,
    WALK_OAK_LATE,
    WALK_PINE,
    make_test_gps_layer,
    make_test_roads_layer,
)
from roads_completion import RoadsCompletionConfig, run_roads_completion

WALKED_LAYER = "walked"
CHECKLIST_LAYER = "checklist"
TEST_BUFFER = 50


def _config(roads, gps, paths) -> RoadsCompletionConfig:
    return RoadsCompletionConfig(
        road_layer=roads,
        gps_layer=gps,
        walked_gpkg_path=paths["walked"],
        checklist_gpkg_path=paths["checklist"],
        walked_layer_name=WALKED_LAYER,
        checklist_layer_name=CHECKLIST_LAYER,
        buffer_dist=TEST_BUFFER,
        completion_threshold=70,
        project=QgsProject.instance(),
        verbose=False,
    )


def _open_layer(gpkg_path: str, layer_name: str) -> QgsVectorLayer:
    layer = QgsVectorLayer(f"{gpkg_path}|layername={layer_name}", layer_name, "ogr")
    assert layer.isValid()
    return layer


def test_first_run_writes_gpkg_and_unique_checklist(qgs_app, roads_completion_paths):
    QgsProject.instance().clear()
    roads = make_test_roads_layer()
    gps = make_test_gps_layer([WALK_OAK_EARLY, WALK_PINE])

    result = run_roads_completion(_config(roads, gps, roads_completion_paths))

    assert set(result.added_filenames) == {
        "walk_oak_early.gpx",
        "walk_pine.gpx",
    }
    assert result.walked_features_added > 0
    assert os.path.isfile(roads_completion_paths["walked"])
    assert os.path.isfile(roads_completion_paths["checklist"])

    walked = _open_layer(roads_completion_paths["walked"], WALKED_LAYER)
    checklist = _open_layer(roads_completion_paths["checklist"], CHECKLIST_LAYER)

    checklist_names = [f["name"] for f in checklist.getFeatures()]
    assert len(checklist_names) == len(set(checklist_names))
    assert set(checklist_names) == {OAK_ST, PINE_ST}

    walked_filenames = {f["filename"] for f in walked.getFeatures()}
    assert "walk_oak_early.gpx" in walked_filenames
    assert "walk_pine.gpx" in walked_filenames


def test_second_run_skips_known_filenames(qgs_app, roads_completion_paths):
    QgsProject.instance().clear()
    roads = make_test_roads_layer()
    gps = make_test_gps_layer([WALK_OAK_EARLY, WALK_PINE])
    config = _config(roads, gps, roads_completion_paths)

    run_roads_completion(config)
    walked_after_first = _open_layer(
        roads_completion_paths["walked"], WALKED_LAYER
    ).featureCount()

    second = run_roads_completion(config)

    assert second.added_filenames == []
    assert set(second.skipped_filenames) == {
        "walk_oak_early.gpx",
        "walk_pine.gpx",
    }
    assert second.walked_features_added == 0

    walked_after_second = _open_layer(
        roads_completion_paths["walked"], WALKED_LAYER
    ).featureCount()
    assert walked_after_second == walked_after_first


def test_third_run_adds_net_new_oak_segment(qgs_app, roads_completion_paths):
    QgsProject.instance().clear()
    roads = make_test_roads_layer()

    run_roads_completion(
        _config(roads, make_test_gps_layer([WALK_OAK_EARLY, WALK_PINE]), roads_completion_paths)
    )
    walked_mid = _open_layer(roads_completion_paths["walked"], WALKED_LAYER)
    oak_mid = [f for f in walked_mid.getFeatures() if f["name"] == OAK_ST]
    assert len(oak_mid) >= 1

    third = run_roads_completion(
        _config(roads, make_test_gps_layer([WALK_OAK_LATE]), roads_completion_paths)
    )

    assert third.added_filenames == ["walk_oak_late.gpx"]
    assert third.walked_features_added >= 1

    walked_final = _open_layer(roads_completion_paths["walked"], WALKED_LAYER)
    oak_feats = [f for f in walked_final.getFeatures() if f["name"] == OAK_ST]
    assert len(oak_feats) >= 2

    start_dates = {
        f["start_date"].toString("yyyy-MM-dd")
        for f in oak_feats
        if f["start_date"] and f["start_date"].isValid()
    }
    assert "2024-01-01" in start_dates
    assert "2024-02-01" in start_dates

    checklist = _open_layer(roads_completion_paths["checklist"], CHECKLIST_LAYER)
    oak_rows = [f for f in checklist.getFeatures() if f["name"] == OAK_ST]
    assert len(oak_rows) == 1


def test_temporal_attributes_preserved_on_walked(qgs_app, roads_completion_paths):
    QgsProject.instance().clear()
    roads = make_test_roads_layer()
    gps = make_test_gps_layer([WALK_OAK_EARLY])

    run_roads_completion(_config(roads, gps, roads_completion_paths))

    walked = _open_layer(roads_completion_paths["walked"], WALKED_LAYER)
    feat = next(walked.getFeatures())
    assert feat["filename"] == "walk_oak_early.gpx"
    assert feat["start_date"].isValid()
    assert feat["end_date"].isValid()
    assert not feat.geometry().isEmpty()
