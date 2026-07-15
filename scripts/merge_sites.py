"""
merge_sites.py
Merges one or more data/sites_<state>.json files (written by that state's
scripts/extract_<state>.py) into the combined data/sites.json that
build_map.py actually reads from.

Replaces -- never appends -- any existing entries for the given state(s),
so re-running an extractor and then this script is always safe to repeat
and never produces duplicates.

Usage: python3 merge_sites.py <state_abbr> [<state_abbr> ...]
Example: python3 merge_sites.py va la
"""
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITES_PATH = os.path.join(REPO_ROOT, 'data', 'sites.json')

if len(sys.argv) < 2:
    print("Usage: python3 merge_sites.py <state_abbr> [<state_abbr> ...]")
    print("Example: python3 merge_sites.py va la")
    sys.exit(1)

states = [s.upper() for s in sys.argv[1:]]

with open(SITES_PATH) as f:
    sites = json.load(f)

new_by_state = {}
for st in states:
    path = os.path.join(REPO_ROOT, 'data', f'sites_{st.lower()}.json')
    if not os.path.exists(path):
        print(f"[skip] {path} not found -- run scripts/extract_{st.lower()}.py first")
        continue
    with open(path) as f:
        new_by_state[st] = json.load(f)

if not new_by_state:
    print("Nothing to merge.")
    sys.exit(1)

before = len(sites)
sites = [s for s in sites if s['state'] not in new_by_state]
for st, new_sites in new_by_state.items():
    sites += new_sites
    print(f"{st}: {len(new_sites)} sites")

with open(SITES_PATH, 'w') as f:
    json.dump(sites, f)

print(f"data/sites.json: {before} -> {len(sites)} total sites")
