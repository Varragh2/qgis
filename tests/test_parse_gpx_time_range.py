"""Unit tests for GPX timestamp parsing."""

from pathlib import Path

import pytest
from gpx_geopackage_loader import parse_gpx_time_range
from qgis.PyQt.QtCore import QDateTime

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_parse_min_max_times(qgs_app):
    start, end = parse_gpx_time_range(str(FIXTURES / "minimal_track.gpx"))
    assert start is not None
    assert end is not None
    assert start.toString("yyyy-MM-dd HH:mm:ss") == "2024-01-15 08:00:00"
    assert end.toString("yyyy-MM-dd HH:mm:ss") == "2024-01-15 09:00:00"
    assert start < end


def test_parse_two_tracks_uses_global_min_max(qgs_app):
    start, end = parse_gpx_time_range(str(FIXTURES / "two_tracks.gpx"))
    assert start.toString("yyyy-MM-dd HH:mm:ss") == "2024-02-01 10:00:00"
    assert end.toString("yyyy-MM-dd HH:mm:ss") == "2024-02-01 11:30:00"


def test_parse_no_timestamps_returns_none(qgs_app):
    start, end = parse_gpx_time_range(str(FIXTURES / "no_timestamps.gpx"))
    assert start is None
    assert end is None


def test_parse_missing_file_returns_none(qgs_app):
    start, end = parse_gpx_time_range(str(FIXTURES / "does_not_exist.gpx"))
    assert start is None
    assert end is None


def test_parse_malformed_xml_returns_none(qgs_app, tmp_path):
    bad = tmp_path / "bad.gpx"
    bad.write_text("<not valid xml", encoding="utf-8")
    start, end = parse_gpx_time_range(str(bad))
    assert start is None
    assert end is None
