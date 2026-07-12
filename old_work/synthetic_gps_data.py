import datetime
import random
import math
import os


def create_long_walk(filename, start_lat, start_lon, steps=2000, step_dist=0.00015):
    """
    Generates a synthetic GPX file with a long random walk.
    - steps: Number of points (higher = longer duration/file)
    - step_dist: Distance between points (higher = faster travel/more area)
    """
    
    gpx_tpl = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="PythonScript" xmlns="http://www.topografix.com/GPX/1/1">',
        '  <trk>',
        '    <name>Long Synthetic Explorer Trace</name>',
        '    <trkseg>'
    ]
    
    curr_lat, curr_lon = start_lat, start_lon
    # Set start date (e.g., June 1st)
    curr_time = datetime.datetime(2024, 6, 1, 10, 0, 0)
    
    for i in range(steps):
        # Move in a semi-random direction to simulate a path
        angle = random.uniform(0, 2 * math.pi)
        curr_lat += step_dist * math.cos(angle)
        curr_lon += step_dist * math.sin(angle)
        
        # Advance time by 10-30 seconds per point
        curr_time += datetime.timedelta(seconds=random.randint(10, 30))
        
        timestamp = curr_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        gpx_tpl.append(f'      <trkpt lat="{curr_lat:.6f}" lon="{curr_lon:.6f}"><time>{timestamp}</time></trkpt>')
    
    gpx_tpl.extend(['    </trkseg>', '  </trk>', '</gpx>'])
    
    # Save to your desktop
    desktop_path = os.path.expanduser("~/Documents/qgis/synthetic_data/" + filename)
    with open(desktop_path, 'w') as f:
        f.write("\n".join(gpx_tpl))
    
    print(f"File saved to: {desktop_path}")

# --- EXECUTION ---
# Adjust coordinates for your specific city


create_long_walk("overlapping_synthetic_trace_01.gpx", start_lat=37.75786758083427, start_lon=-122.44819937226092, steps=1500)
