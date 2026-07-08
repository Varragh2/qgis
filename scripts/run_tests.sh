#!/bin/bash
# Run GPX loader tests with QGIS's bundled Python.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

PREFIX=""
if [[ -n "${QGIS_PREFIX_PATH:-}" && -d "${QGIS_PREFIX_PATH}" ]]; then
  PREFIX="${QGIS_PREFIX_PATH}"
else
  for candidate in \
    /Applications/QGIS-final-4_2_0.app/Contents/MacOS \
    /Applications/QGIS-final-4_0_2.app/Contents/MacOS \
    /Applications/QGIS.app/Contents/MacOS \
    /Applications/QGIS-LTR.app/Contents/MacOS \
    /Applications/QGIS*.app/Contents/MacOS; do
    if [[ -d "$candidate" ]]; then
      PREFIX="$candidate"
      break
    fi
  done
fi

if [[ -z "$PREFIX" ]]; then
  echo "QGIS installation not found; set QGIS_PREFIX_PATH." >&2
  exit 1
fi

CONTENTS_DIR="$(cd "$PREFIX/.." && pwd)"
export QGIS_PREFIX_PATH="$PREFIX"
export PYTHONHOME="${CONTENTS_DIR}/Frameworks"
export QT_QPA_PLATFORM=offscreen
export PROJ_DATA="${CONTENTS_DIR}/Resources/qgis/proj"
export GDAL_DATA="${CONTENTS_DIR}/Resources/qgis/gdal"

PYTHON="${PREFIX}/python3.12"
if [[ ! -x "$PYTHON" ]]; then
  echo "QGIS Python not found at $PYTHON" >&2
  exit 1
fi

cd "$ROOT"
"$PYTHON" -m pytest tests/ -v "$@"
