"""Pytest fixtures for QGIS headless tests."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _default_qgis_prefix() -> str | None:
    env = os.environ.get("QGIS_PREFIX_PATH")
    if env and os.path.isdir(env):
        return env
    candidates = [
        "/Applications/QGIS.app/Contents/MacOS",
        "/Applications/QGIS-final-4_0_2.app/Contents/MacOS",
        "/Applications/QGIS-LTR.app/Contents/MacOS",
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    return None


def _configure_qgis_runtime() -> str | None:
    prefix = _default_qgis_prefix()
    if not prefix:
        return None

    contents_dir = Path(prefix).parent
    os.environ.setdefault("QGIS_PREFIX_PATH", prefix)
    os.environ.setdefault("PYTHONHOME", str(contents_dir / "Frameworks"))
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("PROJ_DATA", str(contents_dir / "Resources/qgis/proj"))
    os.environ.setdefault("GDAL_DATA", str(contents_dir / "Resources/qgis/gdal"))
    return prefix


QGIS_PREFIX = _configure_qgis_runtime()

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture(scope="session")
def qgs_app():
    if not QGIS_PREFIX:
        pytest.skip("QGIS installation not found; set QGIS_PREFIX_PATH")

    from qgis.core import QgsApplication

    QgsApplication.setPrefixPath(QGIS_PREFIX, True)
    app = QgsApplication([], False)
    app.initQgis()
    yield app
    app.exitQgis()


@pytest.fixture
def gpx_inbox(tmp_path):
    """Copy fixture GPX files into a temporary inbox directory."""
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for gpx in FIXTURES_DIR.glob("*.gpx"):
        shutil.copy(gpx, inbox / gpx.name)
    return inbox


@pytest.fixture
def gpkg_path(tmp_path):
    return str(tmp_path / "test_temporal.gpkg")
