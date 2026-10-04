import datetime
import json
import os
import sys
import pandas as pd

import provenance as prov_mod

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Unlike the older extractors, the source CSV path is configurable so this
# can run both on a developer machine (sibling checkout) and in CI, where
# the WV repo is cloned next to this one by the refresh-wv workflow:
#   1. first CLI argument, if given
#   2. WV_SCREENER_CSV environment variable
#   3. ../WestVirginiaDCScreener/outputs/csv/top_candidates_wv.csv
DEFAULT_CSV = os.path.join(
    os.path.dirname(REPO_ROOT),
    'WestVirginiaDCScreener', 'outputs', 'csv', 'top_candidates_wv.csv')
CSV_PATH = (sys.argv[1] if len(sys.argv) > 1 else None) \
    or os.environ.get('WV_SCREENER_CSV') or DEFAULT_CSV

if not os.path.exists(CSV_PATH):
    sys.exit(f"WV candidates CSV not found at {CSV_PATH} — pass the path as "
             f"an argument or set WV_SCREENER_CSV")

df = pd.read_csv(CSV_PATH)

BAD = {"none", "nan", "null", ""}

def clean_owner(v):
    s = str(v).strip()
    if s.lower() in BAD:
        return ""
    return s

def acres_of(row):
    for c in ("parcel_acres", "cad_acres", "osm_acres"):
        v = row.get(c)
        if pd.notna(v) and str(v).strip().lower() not in BAD:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None

sites = []
for _, r in df.iterrows():
    # WV county names arrive bare and uppercase ("HARRISON") — no
    # " County" suffix to strip, unlike some other states' sources.
    sites.append({
        "state": "WV",
        "name": str(r["Plant_Name"]).strip(),
        "county": str(r["County"]).title().strip() if pd.notna(r["County"]) else "",
        "city": str(r["City"]).title().strip() if pd.notna(r["City"]) else "",
        "lat": float(r["Latitude"]),
        "lon": float(r["Longitude"]),
        "score": float(r["total_score"]),
        "acres": acres_of(r),
        "owner": clean_owner(r.get("current_owner", "")),
        "conf": str(r.get("retirement_confidence", "")).strip(),
        "type": str(r.get("brownfield_type", "")).strip(),
        "rank": int(r["rank"]),
    })

with open(os.path.join(REPO_ROOT, 'data', 'sites_wv.json'), 'w') as f:
    json.dump(sites, f)

# Record provenance in the same run that writes the data, so the two cannot
# drift and nobody has to remember a second step. merge_sites.py refuses to
# merge a state whose entry is missing or incomplete.
#
# The source commit is read from the upstream checkout the CSV came out of,
# which is the WV repo cloned beside this one (locally) or into wv-screener/
# (in the refresh workflow). If the CSV is not inside a git checkout the commit
# comes back None and record_live raises rather than writing a hole.
source_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(CSV_PATH))))
source_commit = prov_mod.git_commit(source_dir)

# as_of is the DATA's date, not today's. It comes from the last upstream commit
# that changed outputs/, so re-running this extractor against an unchanged
# upstream does not reset the clock and make old screening data read as fresh.
as_of = prov_mod.upstream_data_date(source_dir, 'outputs')
pipeline_run = os.environ.get('GITHUB_RUN_URL') or os.environ.get('WV_PIPELINE_RUN') \
    or f"local run {datetime.date.today().isoformat()}"

entry = prov_mod.record_live(
    state='WV',
    source_repo='peyton1754/WestVirginiaDCScreener',
    source_commit=source_commit,
    as_of=as_of,
    extracted_on=datetime.date.today().isoformat(),
    pipeline_run=pipeline_run,
    n_sites=len(sites),
)

print(f"Extracted {len(sites)} WV sites from {CSV_PATH}")
print(f"Provenance: data as_of {entry['as_of']} (upstream commit "
      f"{entry['source_commit'][:12]}), extracted_on {entry['extracted_on']}, "
      f"run {entry['pipeline_run']}")
print(json.dumps(sites[0], indent=2))
print(json.dumps(sites[-1], indent=2))
