import json
import os
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

df = pd.read_csv('/private/tmp/claude-501/-Users-arthurfok/a2187ac2-b16c-4eeb-b501-1cd4af8a7360/scratchpad/repos/MississippiDCScreener/outputs/csv/top_candidates_ms.csv')

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
    sites.append({
        "state": "MS",
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

with open(os.path.join(REPO_ROOT, 'data', 'sites_ms.json'), 'w') as f:
    json.dump(sites, f)

print(f"Extracted {len(sites)} MS sites")
