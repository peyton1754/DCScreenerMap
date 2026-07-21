import json
import os
import pandas as pd
import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

df = pd.read_csv('/private/tmp/claude-501/-Users-arthurfok/a2187ac2-b16c-4eeb-b501-1cd4af8a7360/scratchpad/repos/ArkansasDCScreener/outputs/csv/top_candidates_ar.csv')

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

def clean_county(v):
    # Arkansas's raw CSV mixes sources (FRS/EIA860/SRP) with inconsistent
    # county formatting -- some rows carry a "County"/"COUNTY" suffix, some
    # don't (e.g. "JEFFERSON COUNTY" vs "JEFFERSON" for the same county).
    # Strip it before title-casing, same idea as LA's " Parish" stripping,
    # so the map doesn't show duplicate entries for one real county.
    s = str(v).strip()
    if s.lower().endswith(" county"):
        s = s[: -len(" county")]
    return s.title().strip()

sites = []
for _, r in df.iterrows():
    sites.append({
        "state": "AR",
        "name": str(r["Plant_Name"]).strip(),
        "county": clean_county(r["County"]),
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

with open(os.path.join(REPO_ROOT, 'data', 'sites_ar.json'), 'w') as f:
    json.dump(sites, f)

print(f"Extracted {len(sites)} AR sites")
print(json.dumps(sites[0], indent=2))
print(json.dumps(sites[-1], indent=2))
