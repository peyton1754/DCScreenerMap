"""
Downloads Natural Earth's 10m-resolution rivers & lake centerlines dataset
and filters it down to rivers that actually run through the 8 states this
map covers, using real point-in-polygon tests against data/state_shapes.json
(not bounding boxes, which produce false positives for rivers whose bbox
merely overlaps the region without the river itself passing through it —
e.g. the St. Lawrence and Niagara showed up under a bbox-only filter).

Source: Natural Earth (public domain) via the nvkelso/natural-earth-vector
GitHub mirror, which serves the shapefiles pre-converted to GeoJSON:
  https://github.com/nvkelso/natural-earth-vector

A handful of very minor headwater tributaries are dropped explicitly
(DROP_NAMES below) — they're real but too obscure to be useful map context
at this scale (e.g. "Prairie Dog Town Fork Red", a fork of the Red River).
Virginia's James River (through Richmond) is notably absent from this
dataset at 10m resolution — Natural Earth doesn't carry it as a distinct
line feature here, and rather than hand-draw an unverified path, this
script leaves it out. VA still gets the Potomac, Roanoke, New, and Holston.

Run: python3 process_rivers.py
"""
import json
import os
import requests

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(REPO_ROOT, 'data', 'raw')
RAW_PATH = os.path.join(RAW_DIR, 'ne_10m_rivers_lake_centerlines.geojson')
URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_10m_rivers_lake_centerlines.geojson"
)

TARGET_STATES = ['TN', 'MS', 'KY', 'AL', 'TX', 'ND', 'LA', 'VA', 'AR']
DROP_NAMES = {
    'Cowpasture', 'Prairie Dog Town Fork Red',
    'Double Mountain Fork Brazos', 'S. Branch Potomac',
}
MIN_POINTS_IN_REGION = 4
MIN_FRAC_IN_REGION = 0.10

os.makedirs(RAW_DIR, exist_ok=True)
if not os.path.exists(RAW_PATH):
    print(f"Downloading {URL} ...")
    r = requests.get(URL, timeout=60)
    r.raise_for_status()
    with open(RAW_PATH, 'wb') as f:
        f.write(r.content)
else:
    print(f"[skip] {RAW_PATH} already exists")

with open(RAW_PATH) as f:
    rivers_raw = json.load(f)
with open(os.path.join(REPO_ROOT, 'data', 'state_shapes.json')) as f:
    shapes = json.load(f)


def point_in_ring(x, y, ring):
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1):
            inside = not inside
    return inside


def point_in_any_target_state(x, y):
    for st in TARGET_STATES:
        for ring in shapes[st]['rings']:
            if point_in_ring(x, y, ring):
                return True
    return False


def lines_of(geom):
    t = geom['type']
    coords = geom.get('coordinates') or []
    if t == 'LineString':
        return [coords] if coords else []
    if t == 'MultiLineString':
        return [c for c in coords if c]
    return []


rivers = {}
for feat in rivers_raw['features']:
    name = feat['properties'].get('name')
    if not name or name in DROP_NAMES:
        continue
    for line in lines_of(feat['geometry']):
        n_in = sum(1 for x, y in line if point_in_any_target_state(x, y))
        frac = n_in / len(line) if line else 0
        if n_in >= MIN_POINTS_IN_REGION and frac >= MIN_FRAC_IN_REGION:
            rounded = [[round(x, 4), round(y, 4)] for x, y in line]
            rivers.setdefault(name, []).append(rounded)

print('rivers kept:', sorted(rivers.keys()))
out_path = os.path.join(REPO_ROOT, 'data', 'rivers.json')
with open(out_path, 'w') as f:
    json.dump(rivers, f)
print('size:', os.path.getsize(out_path), 'bytes')
