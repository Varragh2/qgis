"""Integration tests for GPX directory import into GeoPackage."""

import shutil
from pathlib import Path

import pytest
from gpx_geopackage_loader import import_gpx_directory, list_gpx_files
from qgis.core import QgsProject, QgsVectorLayer

LAYER_NAME = "GPS_temporal_data"
TARGET_CRS = "EPSG:3857"

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _open_gpkg_layer(gpkg_path: str) -> QgsVectorLayer:
    layer = QgsVectorLayer(
        f"{gpkg_path}|layername={LAYER_NAME}", LAYER_NAME, "ogr"
    )
    assert layer.isValid(), "GeoPackage layer should be valid"
    return layer


def test_list_gpx_files_sorted(gpx_inbox):
    names = list_gpx_files(str(gpx_inbox))
    assert names == sorted(names)
    assert len(names) == 3
    assert "minimal_track.gpx" in names


def test_first_import_adds_all_features(qgs_app, gpx_inbox, gpkg_path):
    project = QgsProject.instance()
    project.clear()

    result = import_gpx_directory(
        str(gpx_inbox),
        gpkg_path,
        LAYER_NAME,
        TARGET_CRS,
        project,
        add_to_project=False,
        verbose=False,
    )

    assert result.added == 3
    assert result.skipped == 0
    assert not result.errors

    layer = _open_gpkg_layer(gpkg_path)
    assert layer.featureCount() == 3

    by_name = {f["filename"]: f for f in layer.getFeatures()}
    assert set(by_name) == {
        "minimal_track.gpx",
        "two_tracks.gpx",
        "no_timestamps.gpx",
    }

    minimal = by_name["minimal_track.gpx"]
    assert minimal["start_date"].toString("yyyy-MM-dd HH:mm:ss") == "2024-01-15 08:00:00"
    assert minimal["end_date"].toString("yyyy-MM-dd HH:mm:ss") == "2024-01-15 09:00:00"
    assert not minimal.geometry().isEmpty()

    two = by_name["two_tracks.gpx"]
    assert two["start_date"].toString("yyyy-MM-dd HH:mm:ss") == "2024-02-01 10:00:00"
    assert two["end_date"].toString("yyyy-MM-dd HH:mm:ss") == "2024-02-01 11:30:00"

    no_time = by_name["no_timestamps.gpx"]
    assert no_time["start_date"] is None or not no_time["start_date"].isValid()
    assert no_time["end_date"] is None or not no_time["end_date"].isValid()


def test_second_import_skips_all_and_preserves_count(qgs_app, gpx_inbox, gpkg_path):
    project = QgsProject.instance()
    project.clear()

    import_gpx_directory(
        str(gpx_inbox),
        gpkg_path,
        LAYER_NAME,
        TARGET_CRS,
        project,
        add_to_project=False,
        verbose=False,
    )

    second = import_gpx_directory(
        str(gpx_inbox),
        gpkg_path,
        LAYER_NAME,
        TARGET_CRS,
        project,
        add_to_project=False,
        verbose=False,
    )

    assert second.added == 0
    assert second.skipped == 3
    assert not second.errors

    layer = _open_gpkg_layer(gpkg_path)
    assert layer.featureCount() == 3


def test_append_new_file_without_wiping_existing(qgs_app, gpx_inbox, gpkg_path):
    project = QgsProject.instance()
    project.clear()

    import_gpx_directory(
        str(gpx_inbox),
        gpkg_path,
        LAYER_NAME,
        TARGET_CRS,
        project,
        add_to_project=False,
        verbose=False,
    )

    extra = gpx_inbox / "extra_walk.gpx"
    shutil.copy(FIXTURES / "minimal_track.gpx", extra)

    third = import_gpx_directory(
        str(gpx_inbox),
        gpkg_path,
        LAYER_NAME,
        TARGET_CRS,
        project,
        add_to_project=False,
        verbose=False,
    )

    assert third.added == 1
    assert third.skipped == 3

    layer = _open_gpkg_layer(gpkg_path)
    assert layer.featureCount() == 4
    names = {f["filename"] for f in layer.getFeatures()}
    assert "extra_walk.gpx" in names
    assert "minimal_track.gpx" in names


def test_one_feature_per_multi_track_gpx(qgs_app, tmp_path, gpkg_path):
    project = QgsProject.instance()
    project.clear()

    inbox = tmp_path / "inbox"
    inbox.mkdir()
    shutil.copy(FIXTURES / "two_tracks.gpx", inbox / "two_tracks.gpx")

    result = import_gpx_directory(
        str(inbox),
        gpkg_path,
        LAYER_NAME,
        TARGET_CRS,
        project,
        add_to_project=False,
        verbose=False,
    )

    assert result.added == 1
    layer = _open_gpkg_layer(gpkg_path)
    assert layer.featureCount() == 1
