import datetime
import random


def generate_gpx(city_name, center_lat, center_lon, num_points=50):
    gpx_template = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="PythonScript" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Synthetic Trace - {city}</name>
    <trkseg>
{points}
    </trkseg>
  </trk>
</gpx>"""

    point_template = '      <trkpt lat="{lat:.6f}" lon="{lon:.6f}"><time>{time}</time></trkpt>'
    
    points_xml = []
    curr_lat, curr_lon = center_lat, center_lon
    curr_time = datetime.datetime.now() - datetime.timedelta(days=random.randint(1, 30))

    for _ in range(num_points):
        # Small random walk (approx 5-20 meters per step)
        curr_lat += random.uniform(-0.0002, 0.0002)
        curr_lon += random.uniform(-0.0002, 0.0002)
        curr_time += datetime.timedelta(seconds=random.randint(5, 15))
        
        points_xml.append(point_template.format(
            lat=curr_lat,
            lon=curr_lon,
            time=curr_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        ))

    return gpx_template.format(city=city_name, points="\n".join(points_xml))


print(generate_gpx("San Francisco", 37.75736180043439, -122.44771585098479))
