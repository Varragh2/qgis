import processing
from qgis.core import QgsProject, QgsProcessingException

# --- CONFIGURATION ---
INPUT_LAYER_NAME = 'all roads dissolved'
OUTPUT_LAYER_NAME = 'full set 5m buffer'
BUFFER_DIST = 5
SIMPLIFY_TOLERANCE = 2
# ---------------------


def run_trunk_cleanup():
    project = QgsProject.instance()
    
    # FIX: Ensure we get exactly one layer object, not a list
    layers = project.mapLayersByName(INPUT_LAYER_NAME)
    if not layers:
        print(f"Error: Layer '{INPUT_LAYER_NAME}' not found.")
        return
    input_layer = layers[0] # Take the first layer from the list

    try:

        print(f"Step 2/4: Buffering ({BUFFER_DIST}m)...")
        buffered = processing.run("native:buffer", {
            'INPUT': input_layer,
            'DISTANCE': BUFFER_DIST,
            'SEGMENTS': 5,
            'END_CAP_STYLE': 0,
            'JOIN_STYLE': 0,
            'DISSOLVE': False,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })['OUTPUT']

        print(f"Step 3/4: Simplifying ({SIMPLIFY_TOLERANCE}m)...")
        simplified = processing.run("native:simplifygeometries", {
            'INPUT': buffered,
            'METHOD': 0,
            'TOLERANCE': SIMPLIFY_TOLERANCE,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })['OUTPUT']

        print(f"Step 4/4: Extracting Medial Axis into '{OUTPUT_LAYER_NAME}'...")
        # This native tool will produce one row per unique name from the aggregate
        result = processing.run("native:approximatemedialaxis", {
            'INPUT': simplified,
            'MIN_ANGLE': 0,
            'DENSITY': 1,
            'OUTPUT': f'memory:{OUTPUT_LAYER_NAME}'
        })['OUTPUT']
        
        project.addMapLayer(result)
        print("-" * 30)
        print(f"Success! '{OUTPUT_LAYER_NAME}' created.")
        print(f"Feature Count: {result.featureCount()}") # This should match your unique names
        print("-" * 30)

    except QgsProcessingException as e:
        print(f"Processing Error: {e}")


run_trunk_cleanup()

