# GPX loader tests

Tests require **QGIS's bundled Python** (not system Python) so `qgis.core` imports work.

## Setup (macOS, QGIS 4)

Install pytest into QGIS's Python once (adjust the app path if needed):

```bash
export PYTHONHOME="/Applications/QGIS-final-4_0_2.app/Contents/Frameworks"
export QGIS_PREFIX_PATH="/Applications/QGIS-final-4_0_2.app/Contents/MacOS"
QGIS_PYTHON="/Applications/QGIS-final-4_0_2.app/Contents/MacOS/python3.12"
"$QGIS_PYTHON" -m pip install -r requirements-dev.txt
```

If your QGIS install lives elsewhere, set `QGIS_PREFIX_PATH` to that app's `Contents/MacOS` directory.

## Run

From the project root (`Documents/qgis`), use the helper script (sets `PYTHONHOME`, `PROJ_DATA`, `GDAL_DATA`, and offscreen Qt):

```bash
chmod +x scripts/run_tests.sh
./scripts/run_tests.sh
```

Or manually:

```bash
export QGIS_PREFIX_PATH="/Applications/QGIS-final-4_0_2.app/Contents/MacOS"
export PYTHONHOME="/Applications/QGIS-final-4_0_2.app/Contents/Frameworks"
export QT_QPA_PLATFORM=offscreen
export PROJ_DATA="/Applications/QGIS-final-4_0_2.app/Contents/Resources/qgis/proj"
export GDAL_DATA="/Applications/QGIS-final-4_0_2.app/Contents/Resources/qgis/gdal"
/Applications/QGIS-final-4_0_2.app/Contents/MacOS/python3.12 -m pytest tests/ -v
```

## What is covered

- `parse_gpx_time_range`: min/max timestamps from GPX `<time>` elements
- `import_gpx_directory`: one feature per file, filename deduplication, in-place GeoPackage append (no layer wipe on re-import)
