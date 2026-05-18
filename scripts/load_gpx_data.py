import os
from qgis.core import (QgsVectorLayer, QgsProject, QgsFeature,
                       QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsVectorFileWriter)

# --- CONFIGURATION ---
GPX_FOLDER = os.path.expanduser("~/Documents/qgis/synthetic_data")
GPKG_PATH = os.path.expanduser("~/Documents/qgis/geopackages/gps_data.gpkg")
LAYER_NAME = "GPS_data"
TARGET_CRS = "EPSG:3857"
# ---------------------

project = QgsProject.instance()
dest_crs = QgsCoordinateReferenceSystem(TARGET_CRS)

if os.path.exists(GPKG_PATH):
    master_layer = QgsVectorLayer(f"{GPKG_PATH}|layername={LAYER_NAME}", LAYER_NAME, "ogr")
else:
    master_layer = QgsVectorLayer(f"LineString?crs={TARGET_CRS}&field=filename:string(255)", LAYER_NAME, "memory")
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.layerName = LAYER_NAME
    options.driverName = "GPKG"
    QgsVectorFileWriter.writeAsVectorFormatV2(master_layer, GPKG_PATH, project.transformContext(), options)
    master_layer = QgsVectorLayer(f"{GPKG_PATH}|layername={LAYER_NAME}", LAYER_NAME, "ogr")

if not project.mapLayersByName(LAYER_NAME):
    project.addMapLayer(master_layer)

existing_filenames = {feat['filename'] for feat in master_layer.getFeatures()}

master_layer.startEditing()
added_count = 0
skipped_count = 0

print(f"Files: {(os.listdir(GPX_FOLDER))}")
for filename in os.listdir(GPX_FOLDER):
    if filename.endswith(".gpx"):
        if filename in existing_filenames:
            skipped_count += 1
            continue
            
        uri = f"{os.path.join(GPX_FOLDER, filename)}?type=track"
        temp_layer = QgsVectorLayer(uri, "temp", "gpx")
        if temp_layer.isValid():
            xform = QgsCoordinateTransform(temp_layer.crs(), dest_crs, project)
            for feat in temp_layer.getFeatures():
                new_f = QgsFeature(master_layer.fields())
                geom = feat.geometry()
                geom.transform(xform)
                new_f.setGeometry(geom)
                new_f.setAttributes([filename])
                success = master_layer.addFeature(new_f)
                if not success:
                    print("CRITICAL: Feature was rejected by the layer!")
                added_count += 1

master_layer.commitChanges()

print("=" * 30)
print("GPKG IMPORT SUMMARY")
print(f"File Path: {GPKG_PATH}")
print(f"New tracks added: {added_count}")
print(f"Duplicates skipped: {skipped_count}")
print(f"Total tracks in layer: {master_layer.featureCount()}")
print("=" * 30)

