#!/bin/bash
# Run GPX loader tests with QGIS's bundled Python.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="${QGIS_PREFIX_PATH:-/Applications/QGIS-final-4_0_2.app/Contents/MacOS}"

if [[ ! -d "$PREFIX" ]]; then
  PREFIX="/Applications/QGIS.app/Contents/MacOS"
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
