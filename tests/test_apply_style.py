"""Tests for QGIS project styling of roads completion outputs."""

from __future__ import annotations

from pathlib import Path

from qgis.core import (
    QgsProject,
    QgsRuleBasedRenderer,
    QgsVectorLayerTemporalProperties,
)

from apply_style import apply_roads_completion_style
from fixtures.roads_completion_layers import (
    WALK_OAK_EARLY,
    WALK_PINE,
    make_test_gps_layer,
    make_test_roads_layer,
)
from roads_completion import RoadsCompletionConfig, run_roads_completion

WALKED_LAYER = "walked"
CHECKLIST_LAYER = "checklist"
GROUP_NAME = "Roads Completion"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _style_path() -> str:
    return str(_repo_root() / "styles" / "walked.qml")


def _write_roads_completion_outputs(project: QgsProject, paths: dict[str, str]) -> None:
    run_roads_completion(
        RoadsCompletionConfig(
            road_layer=make_test_roads_layer(),
            gps_layer=make_test_gps_layer([WALK_OAK_EARLY, WALK_PINE]),
            walked_gpkg_path=paths["walked"],
            checklist_gpkg_path=paths["checklist"],
            walked_layer_name=WALKED_LAYER,
            checklist_layer_name=CHECKLIST_LAYER,
            buffer_dist=50,
            completion_threshold=70,
            project=project,
            verbose=False,
            register_layers=False,
        )
    )


def _active_rule_labels(layer) -> set[str]:
    renderer = layer.renderer()
    assert isinstance(renderer, QgsRuleBasedRenderer)
    labels: set[str] = set()

    def visit(rule):
        if rule.active() and rule.label():
            labels.add(rule.label())
        for child in rule.children():
            visit(child)

    visit(renderer.rootRule())
    return labels


def _assert_temporal_uses_end_date(layer) -> None:
    temporal = layer.temporalProperties()
    assert temporal.isActive()
    assert (
        temporal.mode()
        == QgsVectorLayerTemporalProperties.ModeFeatureDateTimeInstantFromField
    )
    assert temporal.startField() == "end_date"
    assert temporal.endField() == ""
    assert temporal.accumulateFeatures()


def test_apply_roads_completion_style_groups_layers_and_rules(
    qgs_app, roads_completion_paths
):
    project = QgsProject.instance()
    project.clear()
    _write_roads_completion_outputs(project, roads_completion_paths)

    apply_roads_completion_style(
        project=project,
        walked_gpkg_path=roads_completion_paths["walked"],
        checklist_gpkg_path=roads_completion_paths["checklist"],
        walked_layer_name=WALKED_LAYER,
        checklist_layer_name=CHECKLIST_LAYER,
        group_name=GROUP_NAME,
        style_qml_path=_style_path(),
    )

    group = project.layerTreeRoot().findGroup(GROUP_NAME)
    assert group is not None
    assert [child.name() for child in group.children()] == [
        f"{CHECKLIST_LAYER} copy",
        WALKED_LAYER,
        CHECKLIST_LAYER,
    ]

    layers_by_name = {layer.name(): layer for layer in project.mapLayers().values()}
    assert _active_rule_labels(layers_by_name[f"{CHECKLIST_LAYER} copy"]) == {
        "Completed"
    }
    assert _active_rule_labels(layers_by_name[WALKED_LAYER]) == {"Started"}
    assert _active_rule_labels(layers_by_name[CHECKLIST_LAYER]) == {"Not Started"}

    _assert_temporal_uses_end_date(layers_by_name[f"{CHECKLIST_LAYER} copy"])
    _assert_temporal_uses_end_date(layers_by_name[WALKED_LAYER])
    _assert_temporal_uses_end_date(layers_by_name[CHECKLIST_LAYER])


def test_apply_roads_completion_style_replaces_existing_group(
    qgs_app, roads_completion_paths
):
    project = QgsProject.instance()
    project.clear()
    _write_roads_completion_outputs(project, roads_completion_paths)

    kwargs = {
        "project": project,
        "walked_gpkg_path": roads_completion_paths["walked"],
        "checklist_gpkg_path": roads_completion_paths["checklist"],
        "walked_layer_name": WALKED_LAYER,
        "checklist_layer_name": CHECKLIST_LAYER,
        "group_name": GROUP_NAME,
        "style_qml_path": _style_path(),
    }
    apply_roads_completion_style(**kwargs)
    apply_roads_completion_style(**kwargs)

    root = project.layerTreeRoot()
    assert [group.name() for group in root.findGroups(False)] == [GROUP_NAME]
    assert root.findGroup(GROUP_NAME) is not None
    assert len(project.mapLayersByName(WALKED_LAYER)) == 1
    assert len(project.mapLayersByName(CHECKLIST_LAYER)) == 1
    assert len(project.mapLayersByName(f"{CHECKLIST_LAYER} copy")) == 1


def test_calculate_roads_completed_calls_apply_style():
    source = (_repo_root() / "scripts" / "calculate_roads_completed.py").read_text()

    assert "GROUP_NAME" in source
    assert "STYLE_QML" in source
    assert "from apply_style import apply_roads_completion_style" in source
    assert "register_layers=False" in source
    assert "apply_roads_completion_style(" in source
