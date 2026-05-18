"""Synthetic road and GPS layers for roads_completion tests."""

from __future__ import annotations

from dataclasses import dataclass

from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsVectorLayer
from qgis.PyQt.QtCore import QDateTime

TEST_CRS = "EPSG:3857"

OAK_ST = "Oak St"
PINE_ST = "Pine St"


@dataclass
class GpsWalk:
    filename: str
    start_date: str
    end_date: str
    points: list[tuple[float, float]]


def make_test_roads_layer(crs: str = TEST_CRS) -> QgsVectorLayer:
    layer = QgsVectorLayer(
        f"LineString?crs={crs}&field=name:string(50)",
        "test_roads",
        "memory",
    )
    features = [
        QgsFeature(layer.fields()),
        QgsFeature(layer.fields()),
    ]
    features[0].setGeometry(
        QgsGeometry.fromPolylineXY(
            [QgsPointXY(0, 0), QgsPointXY(1000, 0)]
        )
    )
    features[0].setAttribute("name", OAK_ST)
    features[1].setGeometry(
        QgsGeometry.fromPolylineXY(
            [QgsPointXY(0, 100), QgsPointXY(1000, 100)]
        )
    )
    features[1].setAttribute("name", PINE_ST)

    layer.dataProvider().addFeatures(features)
    layer.updateExtents()
    return layer


def make_test_gps_layer(
    walks: list[GpsWalk],
    crs: str = TEST_CRS,
) -> QgsVectorLayer:
    layer = QgsVectorLayer(
        f"MultiLineString?crs={crs}"
        "&field=filename:string(255)"
        "&field=start_date:datetime"
        "&field=end_date:datetime",
        "test_gps",
        "memory",
    )
    features: list[QgsFeature] = []
    for walk in walks:
        feat = QgsFeature(layer.fields())
        points = [QgsPointXY(x, y) for x, y in walk.points]
        feat.setGeometry(QgsGeometry.fromMultiPolylineXY([points]))
        feat.setAttribute("filename", walk.filename)
        feat.setAttribute(
            "start_date",
            QDateTime.fromString(walk.start_date, "yyyy-MM-dd HH:mm:ss"),
        )
        feat.setAttribute(
            "end_date",
            QDateTime.fromString(walk.end_date, "yyyy-MM-dd HH:mm:ss"),
        )
        features.append(feat)

    layer.dataProvider().addFeatures(features)
    layer.updateExtents()
    return layer


WALK_OAK_EARLY = GpsWalk(
    filename="walk_oak_early.gpx",
    start_date="2024-01-01 08:00:00",
    end_date="2024-01-01 09:00:00",
    points=[(0, 0), (600, 0)],
)

WALK_PINE = GpsWalk(
    filename="walk_pine.gpx",
    start_date="2024-01-02 08:00:00",
    end_date="2024-01-02 09:00:00",
    points=[(0, 100), (500, 100)],
)

WALK_OAK_LATE = GpsWalk(
    filename="walk_oak_late.gpx",
    start_date="2024-02-01 08:00:00",
    end_date="2024-02-01 09:00:00",
    points=[(500, 0), (1000, 0)],
)
