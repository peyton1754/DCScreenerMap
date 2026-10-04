"""
merge_sites.py
Merges one or more data/sites_<state>.json files (written by that state's
scripts/extract_<state>.py) into the combined data/sites.json that
build_map.py actually reads from.

Replaces -- never appends -- any existing entries for the given state(s),
so re-running an extractor and then this script is always safe to repeat
and never produces duplicates.

REFUSES to merge a state that has no complete provenance entry in
data/provenance.json. A state's rows do not reach the combined map until
something on the record says where they came from and when. See
scripts/provenance.py for the contract and why it exists. Pass
--allow-missing-provenance only to inspect what a merge WOULD do; it still
refuses to write.

Usage: python3 merge_sites.py <state_abbr> [<state_abbr> ...]
Example: python3 merge_sites.py va la
"""
import json
import os
import sys

import provenance as prov_mod

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITES_PATH = os.path.join(REPO_ROOT, 'data', 'sites.json')

if len(sys.argv) < 2:
    print("Usage: python3 merge_sites.py <state_abbr> [<state_abbr> ...]")
    print("Example: python3 merge_sites.py va la")
    sys.exit(1)

args = sys.argv[1:]
inspect_only = '--allow-missing-provenance' in args
states = [s.upper() for s in args if not s.startswith('--')]

if not states:
    print("No state given.")
    sys.exit(1)

# Provenance gate. This runs BEFORE anything is read or written, so a state
# with an incomplete entry cannot half-apply.
problems = prov_mod.validate(prov_mod.load(), states)
if problems:
    print("Refusing to merge: provenance is incomplete.", file=sys.stderr)
    for p in problems:
        print(f"  {p}", file=sys.stderr)
    print("\nFix data/provenance.json, or have the extractor record it via "
          "provenance.record_live(). Contract: scripts/provenance.py",
          file=sys.stderr)
    sys.exit(2)

if inspect_only:
    print("--allow-missing-provenance given, but provenance is complete and "
          "this flag never writes. Re-run without it to merge.", file=sys.stderr)
    sys.exit(2)

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

# The provenance count and the real row count must agree, or the recorded
# provenance is describing a different extraction than the one on disk. This is
# the cheap version of the same idea as the gate above: a number nobody checked
# is not evidence.
prov = prov_mod.load()
count_problems = []
for st, new_sites in new_by_state.items():
    declared = prov[st].get('sites')
    if declared != len(new_sites):
        count_problems.append(
            f"  {st}: provenance says {declared} sites, data/sites_{st.lower()}.json "
            f"has {len(new_sites)}")
if count_problems:
    print("Refusing to merge: provenance row counts disagree with the data.",
          file=sys.stderr)
    print('\n'.join(count_problems), file=sys.stderr)
    sys.exit(2)

with open(SITES_PATH, 'w') as f:
    json.dump(sites, f)

print(f"data/sites.json: {before} -> {len(sites)} total sites")
for st in sorted(new_by_state):
    e = prov[st]
    when = e['as_of'] if e['status'] == 'live' else f"on or before {e['extracted_on_or_before']}"
    print(f"  {st}: {e['status']}, {when}, from {e['source_repo']}")
