"""Load GPX tracks from a directory into a temporal GeoPackage layer."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QDateTime

GPX_NS = {"gpx": "http://www.topografix.com/GPX/1/1"}

LAYER_SCHEMA_URI = (
    "MultiLineString?crs={crs}"
    "&field=filename:string(255)"
    "&field=start_date:datetime"
    "&field=end_date:datetime"
)


@dataclass
class ImportResult:
    added: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total_in_layer(self) -> int:
        return self.added + self.skipped


def list_gpx_files(folder: str) -> list[str]:
    """Return sorted .gpx basenames in folder."""
    if not os.path.isdir(folder):
        return []
    return sorted(
        name for name in os.listdir(folder) if name.lower().endswith(".gpx")
    )


def parse_gpx_time_range(path: str) -> tuple[QDateTime | None, QDateTime | None]:
    """Parse min/max timestamps from all gpx:time elements in a GPX file."""
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return None, None

    times: list[QDateTime] = []
    for time_el in root.findall(".//gpx:time", GPX_NS):
        time_str = time_el.text
        if not time_str:
            continue
        clean_time = time_str.replace("Z", "").replace("T", " ")
        dt = QDateTime.fromString(clean_time, "yyyy-MM-dd HH:mm:ss")
        if dt.isValid():
            times.append(dt)

    if not times:
        return None, None
    times.sort()
    return times[0], times[-1]


def existing_filenames(layer: QgsVectorLayer) -> set[str]:
    return {feat["filename"] for feat in layer.getFeatures()}


def _geometries_from_gpx_xml(path: str) -> list[QgsGeometry]:
    """Build line geometries from trkseg/trkpt when the GPX provider is unavailable."""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return []

    geometries: list[QgsGeometry] = []
    for segment in root.findall(".//gpx:trkseg", GPX_NS):
        points: list[QgsPointXY] = []
        for trkpt in segment.findall("gpx:trkpt", GPX_NS):
            lat = trkpt.get("lat")
            lon = trkpt.get("lon")
            if lat is None or lon is None:
                continue
            points.append(QgsPointXY(float(lon), float(lat)))
        if len(points) >= 2:
            geometries.append(QgsGeometry.fromPolylineXY(points))
    return geometries


def _as_multilinestring(geometry: QgsGeometry) -> QgsGeometry:
    """Normalize geometry to MultiLineString for the GeoPackage layer."""
    if QgsWkbTypes.isMultiType(geometry.wkbType()):
        return geometry
    if geometry.type() == QgsWkbTypes.LineGeometry:
        return QgsGeometry.fromMultiPolylineXY([geometry.asPolyline()])
    return geometry


def _merge_geometries(geometries: list[QgsGeometry]) -> QgsGeometry | None:
    if not geometries:
        return None
    if len(geometries) == 1:
        return _as_multilinestring(geometries[0])
    return _as_multilinestring(QgsGeometry.collectGeometry(geometries))


def load_track_geometry(
    path: str, dest_crs: QgsCoordinateReferenceSystem, project: QgsProject
) -> QgsGeometry | None:
    """Load track geometry from a GPX file, reproject, and merge into one geometry."""
    abs_path = os.path.abspath(path)
    uri = f"{abs_path}?type=track"
    temp_layer = QgsVectorLayer(uri, "temp", "gpx")

    source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
    geometries: list[QgsGeometry] = []

    if temp_layer.isValid():
        source_crs = temp_layer.crs()
        for feat in temp_layer.getFeatures():
            geom = feat.geometry()
            if geom is not None and not geom.isEmpty():
                geometries.append(QgsGeometry(geom))
    else:
        geometries = _geometries_from_gpx_xml(abs_path)

    merged = _merge_geometries(geometries)
    if merged is None or merged.isEmpty():
        return None

    xform = QgsCoordinateTransform(source_crs, dest_crs, project)
    merged.transform(xform)
    return merged


def ensure_gpkg_layer(
    gpkg_path: str,
    layer_name: str,
    crs: str,
    project: QgsProject,
) -> QgsVectorLayer:
    """Open or create the GeoPackage layer with the temporal field schema."""
    os.makedirs(os.path.dirname(gpkg_path), exist_ok=True)

    if os.path.exists(gpkg_path):
        layer = QgsVectorLayer(
            f"{gpkg_path}|layername={layer_name}", layer_name, "ogr"
        )
        if layer.isValid():
            return layer

    schema_uri = LAYER_SCHEMA_URI.format(crs=crs)
    mem_layer = QgsVectorLayer(schema_uri, layer_name, "memory")
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.layerName = layer_name
    options.driverName = "GPKG"
    err, _, _, error_message = QgsVectorFileWriter.writeAsVectorFormatV3(
        mem_layer, gpkg_path, project.transformContext(), options
    )
    if err != QgsVectorFileWriter.NoError:
        raise RuntimeError(
            f"Failed to create GeoPackage layer at {gpkg_path}: {error_message}"
        )
    layer = QgsVectorLayer(f"{gpkg_path}|layername={layer_name}", layer_name, "ogr")
    if not layer.isValid():
        raise RuntimeError(f"Failed to create GeoPackage layer at {gpkg_path}")
    return layer


def import_gpx_directory(
    folder: str,
    gpkg_path: str,
    layer_name: str,
    dest_crs_authid: str,
    project: QgsProject | None = None,
    *,
    add_to_project: bool = True,
    verbose: bool = True,
) -> ImportResult:
    """
    Import all .gpx files from folder into the GeoPackage layer.

    Skips files whose filename attribute already exists. Adds one feature per file.
    """
    if project is None:
        project = QgsProject.instance()

    dest_crs = QgsCoordinateReferenceSystem(dest_crs_authid)
    result = ImportResult()

    master_layer = ensure_gpkg_layer(gpkg_path, layer_name, dest_crs_authid, project)

    if add_to_project and not project.mapLayersByName(layer_name):
        project.addMapLayer(master_layer)

    known = existing_filenames(master_layer)
    master_layer.startEditing()

    for filename in list_gpx_files(folder):
        if filename in known:
            result.skipped += 1
            continue

        file_path = os.path.join(folder, filename)
        start_time, end_time = parse_gpx_time_range(file_path)

        if start_time is None and verbose:
            print(f"Warning: No valid timestamps parsed in {filename}")

        geom = load_track_geometry(file_path, dest_crs, project)
        if geom is None or geom.isEmpty():
            result.errors.append(f"{filename}: invalid or empty track geometry")
            continue

        new_feat = QgsFeature(master_layer.fields())
        new_feat.setGeometry(geom)
        new_feat.setAttribute("filename", filename)
        new_feat.setAttribute("start_date", start_time)
        new_feat.setAttribute("end_date", end_time)

        if master_layer.addFeature(new_feat):
            result.added += 1
            known.add(filename)
            if verbose and start_time is not None:
                print(f"Added {filename} ({start_time.toString()} – {end_time.toString()})")
        else:
            result.errors.append(f"{filename}: feature rejected by layer")

    if not master_layer.commitChanges():
        result.errors.append("commitChanges failed")
        master_layer.rollBack()

    return result
