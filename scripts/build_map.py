import json
import os
import sys

import provenance as prov_mod

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(REPO_ROOT, 'data', 'sites.json')) as f:
    sites = json.load(f)

STATE_META = {
    'TN': {'name': 'Tennessee',    'bbox': [-90.31, 34.98, -81.65, 36.68], 'light': '#2a78d6', 'dark': '#3987e5'},
    'MS': {'name': 'Mississippi',  'bbox': [-91.65, 30.17, -88.10, 35.00], 'light': '#1baf7a', 'dark': '#199e70'},
    'KY': {'name': 'Kentucky',     'bbox': [-89.57, 36.50, -81.96, 39.15], 'light': '#eda100', 'dark': '#c98500'},
    'AL': {'name': 'Alabama',      'bbox': [-88.47, 30.14, -84.89, 35.01], 'light': '#008300', 'dark': '#008300'},
    'TX': {'name': 'Texas',        'bbox': [-106.65, 25.84, -93.51, 36.50], 'light': '#4a3aa7', 'dark': '#9085e9'},
    'ND': {'name': 'North Dakota', 'bbox': [-104.05, 45.94, -96.55, 49.00], 'light': '#e34948', 'dark': '#e66767'},
    'LA': {'name': 'Louisiana',    'bbox': [-94.04, 28.86, -88.75, 33.02], 'light': '#e87ba4', 'dark': '#d55181'},
    'VA': {'name': 'Virginia',     'bbox': [-83.68, 36.54, -75.17, 39.47], 'light': '#eb6834', 'dark': '#d95926'},
    'AR': {'name': 'Arkansas',     'bbox': [-94.6162, 33.0021, -89.7308, 36.5019], 'light': '#8a3f10', 'dark': '#a04f16'},
    # WV follows the Arkansas precedent (see README "Color palette"): a 10th
    # hue checked against its actual map neighbors (VA orange, KY amber),
    # kept at the end of dict order, away from MS's green-aqua. Still a
    # stopgap — do not add an 11th color without revisiting that section.
    'WV': {'name': 'West Virginia', 'bbox': [-82.6447, 37.2015, -77.7190, 40.6388], 'light': '#0f9b93', 'dark': '#26c6b9'},
}

# Provenance travels with the payload so the page can state its own data
# vintage. gen_map_html.py renders it into a static banner; nothing reads it at
# runtime. Contract and rationale: scripts/provenance.py.
provenance = prov_mod.load()
prov_problems = prov_mod.validate(provenance, sorted({s['state'] for s in sites}))
if prov_problems:
    print('Refusing to build: provenance is incomplete.', file=sys.stderr)
    for p in prov_problems:
        print(f'  {p}', file=sys.stderr)
    sys.exit(2)

payload = {'sites': sites, 'states': STATE_META, 'provenance': provenance}
with open(os.path.join(REPO_ROOT, 'data', 'map_payload.json'), 'w') as f:
    json.dump(payload, f)
print('rows:', len(sites))
n_frozen = sum(e['sites'] for e in provenance.values() if e['status'] == 'frozen')
print(f'provenance: {len(provenance)} states, {n_frozen} of {len(sites)} sites frozen')
