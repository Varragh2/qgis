"""Apply QGIS layer tree, renderer, and temporal styling to road outputs."""

from __future__ import annotations

import os

from qgis.core import (
    QgsProject,
    QgsRuleBasedRenderer,
    QgsVectorLayer,
    QgsVectorLayerTemporalProperties,
)

RULE_LABELS = {"Not Started", "Started", "Completed"}
TEMPORAL_FIELD = "end_date"


def _remove_existing_group(project: QgsProject, group_name: str) -> None:
    root = project.layerTreeRoot()
    while groups := [
        group for group in root.findGroups(False) if group.name() == group_name
    ]:
        group = groups[0]
        group_layer = group.groupLayer()
        if group_layer is not None:
            project.removeMapLayer(group_layer.id())
        parent = group.parent() or root
        parent.removeChildNode(group)


def _remove_existing_layers(project: QgsProject, layer_names: list[str]) -> None:
    for layer_name in layer_names:
        for layer in project.mapLayersByName(layer_name):
            project.removeMapLayer(layer.id())


def _load_gpkg_layer(
    gpkg_path: str, layer_name: str, display_name: str
) -> QgsVectorLayer:
    layer = QgsVectorLayer(f"{gpkg_path}|layername={layer_name}", display_name, "ogr")
    if not layer.isValid():
        raise RuntimeError(f"Failed to load GeoPackage layer: {display_name}")
    return layer


def _apply_named_rule_style(
    layer: QgsVectorLayer, style_qml_path: str, active_rule_label: str
) -> None:
    if not os.path.isfile(style_qml_path):
        raise FileNotFoundError(f"QML style not found: {style_qml_path}")

    _message, ok = layer.loadNamedStyle(style_qml_path)
    if not ok:
        raise RuntimeError(f"Failed to load QML style for {layer.name()}")

    renderer = layer.renderer()
    if not isinstance(renderer, QgsRuleBasedRenderer):
        raise RuntimeError(f"QML style is not rule-based for {layer.name()}")

    def configure_rule(rule: QgsRuleBasedRenderer.Rule) -> None:
        label = rule.label()
        if label in RULE_LABELS:
            rule.setActive(label == active_rule_label)
        for child in rule.children():
            configure_rule(child)

    configure_rule(renderer.rootRule())
    layer.triggerRepaint()


def _apply_temporal_properties(layer: QgsVectorLayer) -> None:
    temporal = layer.temporalProperties()
    temporal.setIsActive(True)
    temporal.setMode(QgsVectorLayerTemporalProperties.ModeFeatureDateTimeInstantFromField)
    temporal.setStartField(TEMPORAL_FIELD)
    temporal.setEndField("")
    temporal.setAccumulateFeatures(True)


def apply_roads_completion_style(
    project: QgsProject,
    walked_gpkg_path: str,
    checklist_gpkg_path: str,
    walked_layer_name: str,
    checklist_layer_name: str,
    group_name: str,
    style_qml_path: str,
) -> list[QgsVectorLayer]:
    """Add styled roads completion layers to a QGIS group."""
    checklist_copy_name = f"{checklist_layer_name} copy"
    _remove_existing_layers(
        project, [walked_layer_name, checklist_layer_name, checklist_copy_name]
    )
    _remove_existing_group(project, group_name)

    layers = [
        (
            _load_gpkg_layer(
                checklist_gpkg_path, checklist_layer_name, checklist_copy_name
            ),
            "Completed",
        ),
        (
            _load_gpkg_layer(walked_gpkg_path, walked_layer_name, walked_layer_name),
            "Started",
        ),
        (
            _load_gpkg_layer(
                checklist_gpkg_path, checklist_layer_name, checklist_layer_name
            ),
            "Not Started",
        ),
    ]

    root = project.layerTreeRoot()
    group = root.addGroup(group_name)
    styled_layers: list[QgsVectorLayer] = []
    for layer, active_rule_label in layers:
        _apply_named_rule_style(layer, style_qml_path, active_rule_label)
        _apply_temporal_properties(layer)
        project.addMapLayer(layer, False)
        group.addLayer(layer)
        styled_layers.append(layer)

    return styled_layers
