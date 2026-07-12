"""Headless QGIS runtime setup used by the command-line entry point."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _prefix_path() -> Path | None:
    configured = os.environ.get("QGIS_PREFIX_PATH")
    if configured and Path(configured).is_dir():
        return Path(configured)
    for app in ("QGIS.app", "QGIS-LTR.app"):
        prefix = Path("/Applications") / app / "Contents/MacOS"
        if prefix.is_dir():
            return prefix
    for prefix in sorted(Path("/Applications").glob("QGIS*.app/Contents/MacOS")):
        if prefix.is_dir():
            return prefix
    return None


def ensure_qgis_python() -> None:
    """Re-exec with QGIS's bundled Python when launched with system Python."""
    prefix = _prefix_path()
    if prefix is None:
        raise RuntimeError(
            "QGIS was not found. Set QGIS_PREFIX_PATH to its Contents/MacOS directory."
        )
    bundled_python = next(
        (path for path in sorted(prefix.glob("python3*")) if path.is_file() and os.access(path, os.X_OK)),
        None,
    )
    if bundled_python is None:
        raise RuntimeError(f"QGIS Python was not found in {prefix}")
    environment = os.environ.copy()
    environment["QGIS_PREFIX_PATH"] = str(prefix)
    environment.setdefault("PYTHONHOME", str(prefix.parent / "Frameworks"))
    environment.setdefault("QT_QPA_PLATFORM", "offscreen")
    environment.setdefault("PROJ_DATA", str(prefix.parent / "Resources/qgis/proj"))
    environment.setdefault("GDAL_DATA", str(prefix.parent / "Resources/qgis/gdal"))
    if Path(sys.executable).resolve() != bundled_python.resolve():
        os.execve(str(bundled_python), [str(bundled_python), *sys.argv], environment)
    os.environ.update(environment)


def initialize_qgis():
    """Start QGIS without a GUI and initialize processing algorithms."""
    ensure_qgis_python()
    from qgis.core import QgsApplication

    prefix = _prefix_path()
    assert prefix is not None
    QgsApplication.setPrefixPath(str(prefix), True)
    app = QgsApplication([], False)
    app.initQgis()

    plugins_path = prefix.parent / "Resources/qgis/python/plugins"
    if plugins_path.is_dir() and str(plugins_path) not in sys.path:
        sys.path.insert(0, str(plugins_path))
    from processing.core.Processing import Processing

    Processing.initialize()
    return app, Processing
