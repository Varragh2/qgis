"""Compute walked-road segments and completion checklist from GPS tracks."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from qgis.core import (
    QgsFeature,
    QgsFields,
    QgsGeometry,
    QgsProject,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
)

WALKED_SCHEMA_URI = (
    "MultiLineString?crs={crs}"
    "&field=name:string(255)"
    "&field=filename:string(255)"
    "&field=start_date:datetime"
    "&field=end_date:datetime"
    "&field=length_m:double"
    "&field=walked_len:double"
)

CHECKLIST_SCHEMA_URI = (
    "MultiLineString?crs={crs}"
    "&field=name:string(255)"
    "&field=length_m:double"
    "&field=walked_len:double"
    "&field=percent_walked:double"
    "&field=completed:integer"
    "&field=start_date:datetime"
    "&field=end_date:datetime"
)


@dataclass
class CompletionResult:
    added_filenames: list[str] = field(default_factory=list)
    skipped_filenames: list[str] = field(default_factory=list)
    walked_features_added: int = 0
    walked_gpkg_path: str = ""
    checklist_gpkg_path: str = ""
    errors: list[str] = field(default_factory=list)


@dataclass
class RoadsCompletionConfig:
    road_layer: QgsVectorLayer
    gps_layer: QgsVectorLayer
    walked_gpkg_path: str
    checklist_gpkg_path: str
    walked_layer_name: str
    checklist_layer_name: str
    buffer_dist: float
    completion_threshold: float
    crs: str = "EPSG:3857"
    project: QgsProject | None = None
    verbose: bool = True
    register_layers: bool = True


def existing_processed_filenames(walked_layer: QgsVectorLayer) -> set[str]:
    """Return GPS filenames already present in the walked output layer."""
    names: set[str] = set()
    if walked_layer.fields().indexFromName("filename") < 0:
        return names
    for feat in walked_layer.getFeatures():
        value = feat["filename"]
        if value:
            names.add(value)
    return names


def _clone_layer_subset(
    source: QgsVectorLayer, features: list[QgsFeature], layer_name: str
) -> QgsVectorLayer:
    crs = source.crs().authid()
    geom_type = QgsWkbTypes.displayString(source.wkbType())
    mem = QgsVectorLayer(f"{geom_type}?crs={crs}", layer_name, "memory")
    provider = mem.dataProvider()
    provider.addAttributes(source.fields().toList())
    mem.updateFields()
    provider.addFeatures(features)
    mem.updateExtents()
    return mem


def filter_gps_by_new_filenames(
    gps_layer: QgsVectorLayer, known_filenames: set[str]
) -> tuple[QgsVectorLayer, list[str], list[str]]:
    """Return a memory layer containing only GPS tracks not yet processed."""
    new_features: list[QgsFeature] = []
    skipped: list[str] = []
    added_names: list[str] = []

    for feat in gps_layer.getFeatures():
        filename = feat["filename"]
        if not filename:
            continue
        if filename in known_filenames:
            skipped.append(filename)
            continue
        new_features.append(QgsFeature(feat))
        added_names.append(filename)

    if not new_features:
        empty = QgsVectorLayer(
            f"{QgsWkbTypes.displayString(gps_layer.wkbType())}?crs={gps_layer.crs().authid()}",
            "filtered_gps",
            "memory",
        )
        empty.dataProvider().addAttributes(gps_layer.fields().toList())
        empty.updateFields()
        return empty, added_names, skipped

    return _clone_layer_subset(gps_layer, new_features, "filtered_gps"), added_names, skipped


def _processing_plugins_path() -> str:
    from qgis.core import QgsApplication

    macos_dir = QgsApplication.prefixPath()
    contents_dir = os.path.dirname(macos_dir)
    return os.path.join(contents_dir, "Resources", "qgis", "python", "plugins")


def _processing_run(algorithm: str, params: dict):
    import sys

    plugins_path = _processing_plugins_path()
    if plugins_path not in sys.path:
        sys.path.insert(0, plugins_path)
    import processing

    return processing.run(algorithm, params)


def dissolve_roads_with_length(road_layer: QgsVectorLayer) -> QgsVectorLayer:
    """Dissolve roads by name and attach total length_m."""
    dissolved = _processing_run(
        "native:dissolve",
        {"INPUT": road_layer, "FIELD": ["name"], "OUTPUT": "TEMPORARY_OUTPUT"},
    )["OUTPUT"]
    return _processing_run(
        "native:fieldcalculator",
        {
            "INPUT": dissolved,
            "FIELD_NAME": "length_m",
            "FIELD_TYPE": 0,
            "FORMULA": "$length",
            "OUTPUT": "TEMPORARY_OUTPUT",
        },
    )["OUTPUT"]


def intersect_roads_with_gps(
    roads_dissolved: QgsVectorLayer,
    gps_layer: QgsVectorLayer,
    buffer_m: float,
) -> QgsVectorLayer:
    """Buffer GPS tracks and intersect with dissolved roads (preserves GPS attributes)."""
    if gps_layer.featureCount() == 0:
        return QgsVectorLayer(
            "MultiLineString?crs=" + roads_dissolved.crs().authid(),
            "empty_intersection",
            "memory",
        )

    gps_buffer = _processing_run(
        "native:buffer",
        {
            "INPUT": gps_layer,
            "DISTANCE": buffer_m,
            "DISSOLVE": False,
            "OUTPUT": "TEMPORARY_OUTPUT",
        },
    )["OUTPUT"]

    return _processing_run(
        "native:intersection",
        {
            "INPUT": roads_dissolved,
            "OVERLAY": gps_buffer,
            "OUTPUT": "TEMPORARY_OUTPUT",
        },
    )["OUTPUT"]


def _union_geometries(geometries: list[QgsGeometry]) -> QgsGeometry | None:
    if not geometries:
        return None
    if len(geometries) == 1:
        return QgsGeometry(geometries[0])
    return QgsGeometry.unaryUnion(geometries)


def _walked_union_by_road_name(walked_layer: QgsVectorLayer) -> dict[str, QgsGeometry]:
    by_name: dict[str, list[QgsGeometry]] = {}
    for feat in walked_layer.getFeatures():
        name = feat["name"]
        geom = feat.geometry()
        if not name or geom is None or geom.isEmpty():
            continue
        by_name.setdefault(name, []).append(QgsGeometry(geom))

    return {
        name: union
        for name, geoms in by_name.items()
        if (union := _union_geometries(geoms)) is not None and not union.isEmpty()
    }


def _has_valid_datetime(value) -> bool:
    return bool(value and hasattr(value, "isValid") and value.isValid())


def _walked_sort_key(feat: QgsFeature) -> tuple[int, int, str]:
    start_date = feat["start_date"]
    filename = feat["filename"] or ""
    if _has_valid_datetime(start_date):
        return (0, start_date.toMSecsSinceEpoch(), filename)
    return (1, 0, filename)


def _completion_dates_by_road_name(
    walked_layer: QgsVectorLayer,
    road_lengths: dict[str, float],
    completion_threshold: float,
) -> dict[str, tuple[object, object]]:
    by_name: dict[str, list[QgsFeature]] = {}
    for feat in walked_layer.getFeatures():
        name = feat["name"]
        geom = feat.geometry()
        if not name or geom is None or geom.isEmpty():
            continue
        by_name.setdefault(name, []).append(QgsFeature(feat))

    completion_dates: dict[str, tuple[object, object]] = {}
    for name, features in by_name.items():
        road_length = road_lengths.get(name) or 0
        if road_length <= 0:
            continue

        cumulative: QgsGeometry | None = None
        for feat in sorted(features, key=_walked_sort_key):
            geom = QgsGeometry(feat.geometry())
            if cumulative is None:
                cumulative = geom
            else:
                cumulative = _union_geometries([cumulative, geom])

            if cumulative is None or cumulative.isEmpty():
                continue

            percent_walked = (cumulative.length() / road_length) * 100
            if percent_walked >= completion_threshold:
                completion_dates[name] = (feat["start_date"], feat["end_date"])
                break

    return completion_dates


def subtract_already_walked(
    segment_layer: QgsVectorLayer,
    walked_layer: QgsVectorLayer,
    target_fields: QgsFields,
) -> list[QgsFeature]:
    """
    For each intersected segment, remove geometry already recorded on that road.

    Returns new features for net-new walked portions only.
    """
    existing = _walked_union_by_road_name(walked_layer)
    output: list[QgsFeature] = []

    for feat in segment_layer.getFeatures():
        road_name = feat["name"]
        geom = feat.geometry()
        if not road_name or geom is None or geom.isEmpty():
            continue

        segment_geom = QgsGeometry(geom)
        if road_name in existing:
            remainder = segment_geom.difference(existing[road_name])
        else:
            remainder = segment_geom

        if remainder is None or remainder.isEmpty():
            continue

        new_feat = QgsFeature(target_fields)
        new_feat.setGeometry(remainder)
        new_feat.setAttribute("name", road_name)
        new_feat.setAttribute("filename", feat["filename"])
        new_feat.setAttribute("start_date", feat["start_date"])
        new_feat.setAttribute("end_date", feat["end_date"])
        new_feat.setAttribute("length_m", feat["length_m"])
        new_feat.setAttribute("walked_len", remainder.length())
        output.append(new_feat)

    return output


def build_checklist_layer(
    roads_dissolved: QgsVectorLayer,
    walked_layer: QgsVectorLayer,
    completion_threshold: float,
) -> QgsVectorLayer:
    """One feature per road name with walked stats, completion flag, and dates."""
    crs = roads_dissolved.crs().authid()
    checklist = QgsVectorLayer(
        CHECKLIST_SCHEMA_URI.format(crs=crs),
        "checklist",
        "memory",
    )
    provider = checklist.dataProvider()

    walked_by_name = _walked_union_by_road_name(walked_layer)
    road_lengths: dict[str, float] = {}
    road_features: list[QgsFeature] = []
    for road in roads_dissolved.getFeatures():
        name = road["name"]
        road_lengths[name] = road["length_m"] or 0
        road_features.append(QgsFeature(road))

    completion_dates = _completion_dates_by_road_name(
        walked_layer, road_lengths, completion_threshold
    )

    output_features: list[QgsFeature] = []
    for road in road_features:
        name = road["name"]
        length_m = road_lengths.get(name) or 0
        walked_geom = walked_by_name.get(name)
        walked_len = walked_geom.length() if walked_geom is not None else 0
        percent_walked = (walked_len / length_m) * 100 if length_m > 0 else 0
        completed = int(percent_walked >= completion_threshold)
        start_date, end_date = completion_dates.get(name, (None, None))

        feat = QgsFeature(checklist.fields())
        feat.setGeometry(QgsGeometry(road.geometry()))
        feat.setAttribute("name", name)
        feat.setAttribute("length_m", length_m)
        feat.setAttribute("walked_len", walked_len)
        feat.setAttribute("percent_walked", percent_walked)
        feat.setAttribute("completed", completed)
        feat.setAttribute("start_date", start_date if completed else None)
        feat.setAttribute("end_date", end_date if completed else None)
        output_features.append(feat)

    provider.addFeatures(output_features)
    checklist.updateExtents()
    return checklist


def ensure_gpkg_layer(
    gpkg_path: str,
    layer_name: str,
    schema_uri: str,
    crs: str,
    project: QgsProject,
) -> QgsVectorLayer:
    os.makedirs(os.path.dirname(gpkg_path) or ".", exist_ok=True)

    if os.path.exists(gpkg_path):
        layer = QgsVectorLayer(
            f"{gpkg_path}|layername={layer_name}", layer_name, "ogr"
        )
        if layer.isValid():
            return layer

    mem_layer = QgsVectorLayer(schema_uri.format(crs=crs), layer_name, "memory")
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
        raise RuntimeError(f"Failed to open GeoPackage layer at {gpkg_path}")
    return layer


def append_features_to_layer(layer: QgsVectorLayer, features: list[QgsFeature]) -> int:
    if not features:
        return 0
    layer.startEditing()
    added = 0
    for feat in features:
        if layer.addFeature(feat):
            added += 1
    if not layer.commitChanges():
        layer.rollBack()
        raise RuntimeError("Failed to commit walked features to GeoPackage")
    return added


def overwrite_gpkg_layer(
    layer: QgsVectorLayer,
    gpkg_path: str,
    layer_name: str,
    project: QgsProject,
) -> QgsVectorLayer:
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.layerName = layer_name
    options.driverName = "GPKG"
    if os.path.exists(gpkg_path):
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

    err, _, _, error_message = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, gpkg_path, project.transformContext(), options
    )
    if err != QgsVectorFileWriter.NoError:
        raise RuntimeError(
            f"Failed to write GeoPackage layer {layer_name}: {error_message}"
        )
    out = QgsVectorLayer(f"{gpkg_path}|layername={layer_name}", layer_name, "ogr")
    if not out.isValid():
        raise RuntimeError(f"Failed to open written layer {layer_name}")
    return out


def _register_layer(
    project: QgsProject, layer: QgsVectorLayer, layer_name: str
) -> QgsVectorLayer:
    existing = project.mapLayersByName(layer_name)
    if existing:
        project.removeMapLayer(existing[0].id())
    project.addMapLayer(layer)
    return layer


def run_roads_completion(config: RoadsCompletionConfig) -> CompletionResult:
    project = config.project or QgsProject.instance()
    result = CompletionResult(
        walked_gpkg_path=config.walked_gpkg_path,
        checklist_gpkg_path=config.checklist_gpkg_path,
    )

    roads_dissolved = dissolve_roads_with_length(config.road_layer)

    walked_gpkg = ensure_gpkg_layer(
        config.walked_gpkg_path,
        config.walked_layer_name,
        WALKED_SCHEMA_URI,
        config.crs,
        project,
    )
    known = existing_processed_filenames(walked_gpkg)

    new_gps, pending_names, skipped = filter_gps_by_new_filenames(
        config.gps_layer, known
    )
    result.skipped_filenames = sorted(set(skipped))

    if new_gps.featureCount() > 0:
        if config.verbose:
            print(
                f"Processing {new_gps.featureCount()} new GPS track(s): "
                f"{', '.join(sorted(set(pending_names)))}"
            )
        intersected = intersect_roads_with_gps(
            roads_dissolved, new_gps, config.buffer_dist
        )
        new_walked = subtract_already_walked(
            intersected, walked_gpkg, walked_gpkg.fields()
        )
        result.walked_features_added = append_features_to_layer(
            walked_gpkg, new_walked
        )
        result.added_filenames = sorted(set(pending_names))
    elif config.verbose:
        print("No new GPS filenames to process; refreshing checklist only.")

    walked_gpkg = QgsVectorLayer(
        f"{config.walked_gpkg_path}|layername={config.walked_layer_name}",
        config.walked_layer_name,
        "ogr",
    )
    checklist_mem = build_checklist_layer(
        roads_dissolved, walked_gpkg, config.completion_threshold
    )
    checklist_gpkg = overwrite_gpkg_layer(
        checklist_mem,
        config.checklist_gpkg_path,
        config.checklist_layer_name,
        project,
    )

    if config.register_layers:
        _register_layer(project, walked_gpkg, config.walked_layer_name)
        _register_layer(project, checklist_gpkg, config.checklist_layer_name)

    if config.verbose:
        print(
            f"Walked features added: {result.walked_features_added}; "
            f"skipped filenames: {len(result.skipped_filenames)}"
        )
        print(f"Walked GPKG: {config.walked_gpkg_path}")
        print(f"Checklist GPKG: {config.checklist_gpkg_path}")

    return result
