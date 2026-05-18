"""Unit tests for roads_completion helpers."""

from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsVectorLayer

from fixtures.roads_completion_layers import OAK_ST, make_test_roads_layer
from roads_completion import (
    existing_processed_filenames,
    subtract_already_walked,
)


def _walked_layer_with_segment(crs: str = "EPSG:3857") -> QgsVectorLayer:
    layer = QgsVectorLayer(
        f"MultiLineString?crs={crs}"
        "&field=name:string(50)"
        "&field=filename:string(255)"
        "&field=start_date:datetime"
        "&field=end_date:datetime"
        "&field=length_m:double"
        "&field=walked_len:double",
        "walked",
        "memory",
    )
    feat = QgsFeature(layer.fields())
    feat.setGeometry(
        QgsGeometry.fromMultiPolylineXY(
            [[QgsPointXY(0, 0), QgsPointXY(600, 0)]]
        )
    )
    feat.setAttribute("name", OAK_ST)
    feat.setAttribute("filename", "walk_oak_early.gpx")
    feat.setAttribute("length_m", 1000.0)
    feat.setAttribute("walked_len", 600.0)
    layer.dataProvider().addFeature(feat)
    return layer


def _segment_layer(crs: str = "EPSG:3857") -> QgsVectorLayer:
    layer = QgsVectorLayer(
        f"MultiLineString?crs={crs}"
        "&field=name:string(50)"
        "&field=filename:string(255)"
        "&field=start_date:datetime"
        "&field=end_date:datetime"
        "&field=length_m:double",
        "segments",
        "memory",
    )
    feat = QgsFeature(layer.fields())
    feat.setGeometry(
        QgsGeometry.fromMultiPolylineXY(
            [[QgsPointXY(500, 0), QgsPointXY(1000, 0)]]
        )
    )
    feat.setAttribute("name", OAK_ST)
    feat.setAttribute("filename", "walk_oak_late.gpx")
    feat.setAttribute("length_m", 1000.0)
    layer.dataProvider().addFeature(feat)
    return layer


def test_existing_processed_filenames(qgs_app):
    walked = _walked_layer_with_segment()
    assert existing_processed_filenames(walked) == {"walk_oak_early.gpx"}


def test_subtract_already_walked_removes_overlap(qgs_app):
    walked = _walked_layer_with_segment()
    segments = _segment_layer()
    target_fields = walked.fields()
    new_feats = subtract_already_walked(segments, walked, target_fields)

    assert len(new_feats) == 1
    geom = new_feats[0].geometry()
    assert not geom.isEmpty()
    assert new_feats[0]["filename"] == "walk_oak_late.gpx"
    assert new_feats[0].geometry().length() < 500 + 1


def test_subtract_already_walked_fully_covered_returns_empty(qgs_app):
    walked = _walked_layer_with_segment()
    layer = QgsVectorLayer(
        "MultiLineString?crs=EPSG:3857"
        "&field=name:string(50)"
        "&field=filename:string(255)"
        "&field=start_date:datetime"
        "&field=end_date:datetime"
        "&field=length_m:double",
        "segments",
        "memory",
    )
    feat = QgsFeature(layer.fields())
    feat.setGeometry(
        QgsGeometry.fromMultiPolylineXY(
            [[QgsPointXY(100, 0), QgsPointXY(400, 0)]]
        )
    )
    feat.setAttribute("name", OAK_ST)
    feat.setAttribute("filename", "walk_oak_late.gpx")
    feat.setAttribute("length_m", 1000.0)
    layer.dataProvider().addFeature(feat)

    new_feats = subtract_already_walked(layer, walked, walked.fields())
    assert new_feats == []
