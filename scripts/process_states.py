import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NAME_TO_ABBR = {
    'Alabama': 'AL', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
    'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
    'District of Columbia': 'DC', 'Florida': 'FL', 'Georgia': 'GA',
    'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME',
    'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI',
    'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
    'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
    'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM',
    'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND',
    'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA',
    'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD',
    'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
    'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV',
    'Wisconsin': 'WI', 'Wyoming': 'WY',
    # Excluded (not continental / off-projection): Alaska, Hawaii, Puerto Rico
}

with open(os.path.join(REPO_ROOT, 'data', 'us_states.geojson')) as f:
    gj = json.load(f)

def round_ring(ring):
    return [[round(lon, 4), round(lat, 4)] for lon, lat in ring]

states = {}
for feat in gj['features']:
    name = feat['properties']['name']
    abbr = NAME_TO_ABBR.get(name)
    if not abbr:
        continue
    geom = feat['geometry']
    polys = []
    if geom['type'] == 'Polygon':
        polys = [geom['coordinates']]
    elif geom['type'] == 'MultiPolygon':
        polys = geom['coordinates']
    rings = []
    for poly in polys:
        for ring in poly:
            rings.append(round_ring(ring))
    states[abbr] = {'name': name, 'rings': rings}

print('states embedded:', len(states))
out_path = os.path.join(REPO_ROOT, 'data', 'state_shapes.json')
with open(out_path, 'w') as f:
    json.dump(states, f)
print('size:', os.path.getsize(out_path), 'bytes')
