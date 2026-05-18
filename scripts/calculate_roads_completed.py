import processing
from qgis.core import QgsProject, QgsProcessingException

# --- CONFIGURATION ---
ROAD_LAYER_NAME = 'sf_roads'        # Your OSM roads
GPS_LAYER_NAME = 'GPS_temporal_data'       # Your GPS tracks
BUFFER_DIST = 15                    # Your "discovery" radius in meters
COMPLETION_THRESHOLD = 70           # % required to mark as 'Conquered'
# Output Layers
WALKED_LAYER = 'Temporal Overlap with gps'
CHECKLIST_LAYER = 'Temporal Roads Completed Checklist'
# ---------------------


def run_completion_pipeline():
    project = QgsProject.instance()
    
    # Get layers
    road_layer = project.mapLayersByName(ROAD_LAYER_NAME)[0]
    gps_layer = project.mapLayersByName(GPS_LAYER_NAME)[0]

    # Dissolve Roads by Name & calculate total length
    print("Step 1: Dissolving roads and calculating full length...")
    roads_dissolved = processing.run("native:dissolve", {
        'INPUT': road_layer,
        'FIELD': ['name'],
        'OUTPUT': 'TEMPORARY_OUTPUT'
    })['OUTPUT']
    
    # Add static 'length_m' field (crucial to do this BEFORE intersection)
    # Since $length includes the unedited roads, the length isn't accurate to what I really walk
    roads_dissolved = processing.run("native:fieldcalculator", {
        'INPUT': roads_dissolved,
        'FIELD_NAME': 'length_m',
        'FIELD_TYPE': 0,
        'FORMULA': '$length',
        'OUTPUT': 'TEMPORARY_OUTPUT'
    })['OUTPUT']

    # 2. Buffer the GPS Trace
    # This step is where I lose the unique filename attributes and start_date
    # Dissolve = True Merges overlaps so you don't double-count distance

    print(f"Step 2: Buffering GPS trace by {BUFFER_DIST}m...")
    gps_buffer = processing.run("native:buffer", {
        'INPUT': gps_layer,
        'DISTANCE': BUFFER_DIST,
        'DISSOLVE': False,
        'OUTPUT': 'TEMPORARY_OUTPUT'
    })['OUTPUT']

    # 3. Intersect (The "Cookie Cutter")
    print("Step 3: Intersecting roads with GPS buffer...")
    intersected = processing.run("native:intersection", {
        'INPUT': roads_dissolved,
        'OVERLAY': gps_buffer,
        'OUTPUT': 'TEMPORARY_OUTPUT'
    })['OUTPUT']

    # 4. Dissolve by Name Again (Merges segments if trace was broken)
    # I loose unique start dates for each road with this step
    # A full road will only ever have one start date, even If I walked two separate parts on different days
    print("Step 4: Consolidating walked segments...")
    walked_dissolved = processing.run("native:dissolve", {
        'INPUT': intersected,
        'FIELD': ['name'],
        'OUTPUT': 'TEMPORARY_OUTPUT'
    })['OUTPUT']

    # 5. Calculate walked_len and Percentage
    print("Step 5: Calculating final stats...")
    # Add 'walked_len'
    final_stats = processing.run("native:fieldcalculator", {
        'INPUT': walked_dissolved,
        'FIELD_NAME': 'walked_len',
        'FIELD_TYPE': 0,
        'FORMULA': '$length',
        'OUTPUT': 'TEMPORARY_OUTPUT'
    })['OUTPUT']

    # Add 'percentage_walked' and 'completed' flag
    final_output = processing.run("native:fieldcalculator", {
        'INPUT': final_stats,
        'FIELD_NAME': 'percent_walked',
        'FIELD_TYPE': 0,
        'FORMULA': '("walked_len" / "length_m") * 100',
        'OUTPUT': 'TEMPORARY_OUTPUT'
    })['OUTPUT']
    
    # Mark as completed (1 for Yes, 0 for No)
    final_output_ready = processing.run("native:fieldcalculator", {
        'INPUT': final_output,
        'FIELD_NAME': 'completed',
        'FIELD_TYPE': 1,
        'FORMULA': f'to_int("percent_walked" >= {COMPLETION_THRESHOLD})',
        'OUTPUT': 'TEMPORARY_OUTPUT'
    })['OUTPUT']

    # This layer should include undissolved features, including duplicate named roads
    # This is because it needs to preserve the start_date for a road each time I visit it
    undissolved_gps_overlay = processing.run("native:joinattributestable", {
        'INPUT': intersected,
        'FIELD': 'name',              # Key in Layer 1
        'INPUT_2': final_output_ready, # Your stats layer
        'FIELD_2': 'name',            # Key in Layer 2
        'FIELDS_TO_COPY': ['percent_walked', 'completed'],
        'METHOD': 0,                  # many:many join
        'DISCARD_NONMATCHING': False, # Keep all roads, even untravelled ones
        'OUTPUT': f'memory:{WALKED_LAYER}'
    })['OUTPUT']



    # STEP 4: Join attributes by Field Value (using "name" as the key)
    print("Joining stats back to checklist via street name...")
    dissolved_road_names = processing.run("native:joinattributestable", {
        'INPUT': roads_dissolved,      # Your full-length geometry
        'FIELD': 'name',              # Key in Layer 1
        'INPUT_2': final_output_ready, # Your stats layer
        'FIELD_2': 'name',            # Key in Layer 2
        'FIELDS_TO_COPY': ['walked_len', 'percent_walked', 'completed', 'start_date'],
        'METHOD': 1,                  # 1:1 join
        'DISCARD_NONMATCHING': False, # Keep all roads, even untravelled ones
        'OUTPUT': f'memory:{CHECKLIST_LAYER}'
    })['OUTPUT']

    project.addMapLayer(dissolved_road_names)
    project.addMapLayer(undissolved_gps_overlay)
    print(f"Success! '{WALKED_LAYER}' and '{CHECKLIST_LAYER}' added.")



run_completion_pipeline()

