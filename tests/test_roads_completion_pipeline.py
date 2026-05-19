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


def _config(roads, gps, paths, completion_threshold: float = 70) -> RoadsCompletionConfig:
    return RoadsCompletionConfig(
        road_layer=roads,
        gps_layer=gps,
        walked_gpkg_path=paths["walked"],
        checklist_gpkg_path=paths["checklist"],
        walked_layer_name=WALKED_LAYER,
        checklist_layer_name=CHECKLIST_LAYER,
        buffer_dist=TEST_BUFFER,
        completion_threshold=completion_threshold,
        project=QgsProject.instance(),
        verbose=False,
    )


def _open_layer(gpkg_path: str, layer_name: str) -> QgsVectorLayer:
    layer = QgsVectorLayer(f"{gpkg_path}|layername={layer_name}", layer_name, "ogr")
    assert layer.isValid()
    return layer


def _datetime_text(value) -> str | None:
    if value and value.isValid():
        return value.toString("yyyy-MM-dd HH:mm:ss")
    return None


def _checklist_feature(layer: QgsVectorLayer, road_name: str):
    return [f for f in layer.getFeatures() if f["name"] == road_name][0]


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
    assert checklist.fields().indexFromName("start_date") >= 0
    assert checklist.fields().indexFromName("end_date") >= 0

    checklist_by_name = {f["name"]: f for f in checklist.getFeatures()}
    assert checklist_by_name[OAK_ST]["completed"] == 0
    assert _datetime_text(checklist_by_name[OAK_ST]["start_date"]) is None
    assert _datetime_text(checklist_by_name[OAK_ST]["end_date"]) is None

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

    dates_by_filename = {
        f["filename"]: _datetime_text(f["start_date"])
        for f in oak_feats
    }
    assert dates_by_filename["walk_oak_early.gpx"] == "2024-01-01 08:00:00"
    assert dates_by_filename["walk_oak_late.gpx"] == "2024-02-01 08:00:00"

    checklist = _open_layer(roads_completion_paths["checklist"], CHECKLIST_LAYER)
    oak_rows = [f for f in checklist.getFeatures() if f["name"] == OAK_ST]
    assert len(oak_rows) == 1
    assert oak_rows[0]["completed"] == 1
    assert _datetime_text(oak_rows[0]["start_date"]) == "2024-02-01 08:00:00"
    assert _datetime_text(oak_rows[0]["end_date"]) == "2024-02-01 09:00:00"

    run_roads_completion(
        _config(roads, make_test_gps_layer([WALK_OAK_LATE]), roads_completion_paths)
    )
    checklist_refreshed = _open_layer(
        roads_completion_paths["checklist"], CHECKLIST_LAYER
    )
    oak_refreshed = [
        f for f in checklist_refreshed.getFeatures() if f["name"] == OAK_ST
    ][0]
    assert _datetime_text(oak_refreshed["start_date"]) == "2024-02-01 08:00:00"
    assert _datetime_text(oak_refreshed["end_date"]) == "2024-02-01 09:00:00"


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


def test_checklist_completion_dates_are_set_once(qgs_app, roads_completion_paths):
    QgsProject.instance().clear()
    roads = make_test_roads_layer()

    run_roads_completion(
        _config(
            roads,
            make_test_gps_layer([WALK_OAK_EARLY]),
            roads_completion_paths,
            completion_threshold=50,
        )
    )

    checklist = _open_layer(roads_completion_paths["checklist"], CHECKLIST_LAYER)
    oak = _checklist_feature(checklist, OAK_ST)
    assert oak["completed"] == 1
    assert _datetime_text(oak["start_date"]) == "2024-01-01 08:00:00"
    assert _datetime_text(oak["end_date"]) == "2024-01-01 09:00:00"

    run_roads_completion(
        _config(
            roads,
            make_test_gps_layer([WALK_OAK_LATE]),
            roads_completion_paths,
            completion_threshold=50,
        )
    )

    checklist_after_later_walk = _open_layer(
        roads_completion_paths["checklist"], CHECKLIST_LAYER
    )
    oak_after_later_walk = _checklist_feature(checklist_after_later_walk, OAK_ST)
    assert oak_after_later_walk["completed"] == 1
    assert (
        _datetime_text(oak_after_later_walk["start_date"])
        == "2024-01-01 08:00:00"
    )
    assert _datetime_text(oak_after_later_walk["end_date"]) == "2024-01-01 09:00:00"
