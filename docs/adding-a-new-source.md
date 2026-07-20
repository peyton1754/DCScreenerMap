# Adding a New Brownfield Source

There is no shared library between the state repos — every
`build_candidates.py` and `enrich_columns.py` is a full copy. Adding a
source means editing it by hand in every repo you want it in, one at a
time. Budget for that when scoping the work: writing the source once and
testing it in one state is the easy part; porting it correctly to 8+
other repos, each with slightly different variable names from its own
fork history, is where the time actually goes.

## First: which kind of source is this?

Two genuinely different things get called "a new source" in this
project, and they're wired in differently:

- **A candidate source** — it finds *new sites* nobody else found.
  Lives in `build_candidates.py`, gets a `source` tag, competes in the
  500m dedup pass. EIA860, GEM Coal Tracker, FRS, TRI, OSM, and the EPA
  Redevelopment Mapper are all this kind.
- **An enrichment / corroboration source** — it adds *metadata* to
  candidates that some other source already found; it never creates a
  new candidate on its own. Lives in `enrich_columns.py`. RCRA
  Corrective Action is this kind: being on the RCRA CA list means a
  site has documented contamination requiring cleanup, which has no
  correlation with whether the facility is retired — a refinery can run
  a corrective-action cleanup on one area while operating at full
  capacity everywhere else. Verified this directly: the raw nationwide
  list is dominated by active facilities (Exxon Mobil, Valero, Dow,
  3M). Making it a full candidate source would flood every state with
  active-facility false positives. As metadata on candidates that
  *already* passed this pipeline's own quality gates, it's useful
  corroboration instead.

If you're not sure which your new dataset is, ask: "would I trust this
list alone to say a site is retired/derelict?" If yes, it's a candidate
source. If no — it's data about contamination, ownership, or some other
fact that's true regardless of operating status — it's corroboration.

---

## Adding a candidate source

### Where it goes

`build_candidates.py` has a numbered list of sources (currently 1
EIA860, 1b GEM Coal Tracker, 2 FRS, 3 TRI, 4 OSM, 5 EPA Redevelopment
Mapper — TRI is absent in Alabama and Texas). Add a new numbered block
in the same style, between whichever existing sources make sense
(insert as its own `1c`, `6`, etc. rather than renumbering everything).

### The common schema

Every source must emit a GeoDataFrame with these exact columns before
it's combined with the others:

```python
{
    "source":         "YOUR_SOURCE_TAG",   # short, uppercase, unique
    "site_id":         ...,                 # unique per site, prefixed
    "Plant_Name":      ...,
    "State":           ...,
    "County":          "",                  # often left blank, filled later
    "Street_Address":  ...,
    "City":            ...,
    "Latitude":        ...,
    "Longitude":       ...,
    "brownfield_type": ...,                 # from the shared NAICS_LABEL
                                             # categories where possible
    "total_mw":        np.nan,              # unless genuinely a power plant
    "retirement_year": np.nan,
    "technology":      "",
    "Grid_Voltage_kV": np.nan,
    "Natural_Gas_Pipeline_Name_1": "",
    "Name_of_Water_Source": "",
    "naics_code":      "",
    "has_air_permit":  False,
    "geometry":        gpd.points_from_xy(lon, lat),
}
```
Build it as a `GeoDataFrame` in `EPSG:4326`, then `.to_crs(TARGET_CRS)`
to match the rest of the pipeline.

### Live API vs. manual-download file

If the dataset has a stable public API or bulk-download URL (like the
EPA Redevelopment Mapper's ArcGIS FeatureServer), fetch it live and
cache the raw response locally so re-runs don't re-download:

```python
CACHE = TENNESSEE / "your_source_<state>.csv"   # TENNESSEE is that repo's
                                                  # own-state raw dir var,
                                                  # despite the name — a
                                                  # fork-lineage leftover,
                                                  # not a bug
if not CACHE.exists():
    resp = requests.get(URL, params={...}, timeout=30)
    resp.raise_for_status()
    df = pd.DataFrame(...)
    df.to_csv(CACHE, index=False)
else:
    df = pd.read_csv(CACHE, low_memory=False)
```

If it doesn't — GEM's Global Coal Plant Tracker is gated behind an
email signup form, not a public API — read a manually-downloaded local
file instead, glob-matched so future dated re-downloads don't need code
changes, and fail with clear instructions rather than a bare exception:

```python
GEM_DIR = TENNESSEE / "gem"
gem_files = sorted(GEM_DIR.glob("Global-Coal-Plant-Tracker*.xlsx")) if GEM_DIR.exists() else []

if not gem_files:
    print(f"  [skip] No GEM Coal Plant Tracker file found in {GEM_DIR}")
    print(f"  Manual download (email signup required): https://...")
    print(f"  Place the downloaded .xlsx in {GEM_DIR}/ (any filename "
          f"starting with 'Global-Coal-Plant-Tracker' works)")
else:
    ...  # parse gem_files[-1]
```

Wrap the whole block in `try/except`, print a `[warn]` on failure, and
fall back to an empty GeoDataFrame with the right schema/CRS — one
source failing (dead URL, changed API shape) should never take down the
rest of the pipeline. This has already happened three times for
unrelated reasons (see "Known gaps" in the main README) and every state
kept running because of this pattern.

### Dedup priority

Near the bottom of `build_candidates.py`, all sources get combined and
deduplicated within 500m, keeping one row per cluster by priority order:

```python
combined["_source_order"] = combined["source"].map(
    {"EIA860": 0, "GEM_COAL": 1, "SRP_REDEV_MAPPER": 2, "FRS": 3, "TRI": 4, "OSM": 5}
).fillna(6)
```

Add your new `source` tag to this dict. Rank it by how trustworthy and
precise the dataset's coordinates and site identity are relative to the
existing sources — a professionally-surveyed federal registry beats a
crowd-sourced polygon centroid. Update the `all_frames = [...]` list a
few lines above too, and the `print("  Priority: ...")` line so the log
output stays accurate.

### Exclusions worth stealing

The EPA Redevelopment Mapper block has two exclusion filters worth
reusing verbatim for any similar "curated large-site" dataset: dropping
sites already marked ready-for-use/redeveloped (you want undeveloped
land, not a site a competitor already built on), and dropping
protected parkland by name-pattern match (`national park`, `wildlife
refuge`, etc.) — legally undevelopable regardless of infrastructure
merit, and this project's own data has included a few (e.g. Palo Alto
Battlefield National Historical Park in Texas' ACRES data).

---

## Adding an enrichment / corroboration source

### Where it goes

`enrich_columns.py` has a series of numbered sections. Add yours after
section 4 (parcel/acreage) as `4b`, `4c`, etc. — that's where the EPA
Redevelopment Mapper acreage override and RCRA CA corroboration
currently live, and downstream code (`score_and_export.py`) expects
these enrichment columns to already exist by the time it runs.

### The pattern

```python
# ===================================================================
# 4d. Your new corroboration source (metadata only, not a candidate source)
# ===================================================================
print("\n" + "=" * 60)
print("4d. Your new corroboration source")
print("=" * 60)

YOUR_CACHE = AL_RAW / "your_source_<state>.csv"   # AL_RAW is that repo's
                                                    # own-state raw dir var
MATCH_RADIUS_M = 500

if "your_new_column" not in cands.columns:
    cands["your_new_column"] = ""

try:
    # ... fetch/load into a GeoDataFrame `pts` in cands.crs ...

    from shapely.strtree import STRtree
    tree = STRtree(pts.geometry.values)
    n_match = 0
    for i in range(len(cands)):
        pt = cands.geometry.iloc[i]
        nearby = tree.query(pt, predicate="dwithin", distance=MATCH_RADIUS_M)
        if len(nearby) == 0:
            continue
        dists = [pt.distance(pts.geometry.iloc[j]) for j in nearby]
        best_j = nearby[dists.index(min(dists))]
        cands.at[cands.index[i], "your_new_column"] = str(pts.iloc[best_j]["SOME_FIELD"])
        n_match += 1

    print(f"  {n_match}/{len(cands)} candidates matched within {MATCH_RADIUS_M}m")
except Exception as _e:
    print(f"  [warn] Your source failed: {_e}")
```

### The one bug that has bitten this exact pattern twice

**Pre-initialize the column before the loop, not just inside it.** If a
run happens to have zero matches, `cands.at[..., "your_new_column"] = ...`
never executes, so the column never gets created on the DataFrame at
all — and `score_and_export.py`'s export step does
`[c for c in EXPORT_COLS if c in export_df.columns]`, which silently
drops any column not actually present, no error raised. This exact bug
hit `acres_source` in Tennessee and Alabama's real output (both had zero
EPA Redevelopment Mapper matches on a given run) despite the column
being correctly listed in `EXPORT_COLS` the whole time. The fix is the
`if "col" not in cands.columns: cands["col"] = ""` line shown above,
copied from how `rcra_corrective_action` already guards against this —
do this **before** writing any matching logic, not after you notice the
column missing from a CSV.

### Don't forget `EXPORT_COLS`

Separately from the pre-init issue above, `score_and_export.py` has an
explicit `EXPORT_COLS` list — your new column also needs to be added
there, or it's dropped from the final CSV regardless of whether the
DataFrame has it. Two independent failure points, both silent, both
required to get right:

```python
EXPORT_COLS = [
    ...
    "parcel_acres", "cad_acres", "osm_acres", "acres_source",
    "retirement_confidence", "retirement_signals", "rcra_corrective_action",
    "your_new_column",   # <-- add it here too
    ...
]
```

Texas is structured slightly differently — `fetch_texas_parcels.py`
plays the role `enrich_columns.py` plays elsewhere, and its
`EXPORT_COLS` entries are split across separately-commented `# Parcel`
and `# Retirement confidence` sections rather than one contiguous list,
but the same requirement applies.

---

## Porting to the other repos

There's no shared code to update once — repeat the edit by hand in
each state repo's `build_candidates.py`/`enrich_columns.py`. A few
things vary repo to repo and will trip up a copy-paste port:

- **Variable names carry fork-lineage leftovers.** `TENNESSEE` and
  `AL_RAW` are common names for "this repo's own state raw-data
  directory" even in repos that are neither Tennessee nor Alabama
  (West Virginia and Kentucky both use these exact names). Check what a
  given repo's variable is actually called — `grep -n "^TENNESSEE\|^AL_RAW\|^ROOT" build_candidates.py` — rather than assuming.
- **Some repos are missing sources others have.** TRI is absent in
  Alabama and Texas; if your new source's exclusion/priority logic
  references `tri_gdf`, guard for its absence.
- **Texas's architecture is different**, not just renamed — it's a
  4-stage pipeline (`build_candidates.py` → `filter_pipeline.py` →
  `fetch_texas_parcels.py` → `score_and_export.py`) where
  `fetch_texas_parcels.py` absorbs what other states split across
  `enrich_retirement.py`/`enrich_columns.py`/`fetch_epa_compliance.py`.
  Your enrichment-source code goes into `fetch_texas_parcels.py` for
  Texas, not a same-named `enrich_columns.py` (Texas doesn't have one).
- **A repo you haven't touched recently may be missing fixes another
  repo already has.** Kentucky was missing three sourcing features
  (including this exact GEM/EPA Redevelopment Mapper/RCRA CA set)
  entirely because it was forked before they existed and never caught
  up — check what a target repo actually has with
  `grep -n "Source 1b\|Source 5\|4c\. RCRA" build_candidates.py enrich_columns.py`
  before assuming it's current.

## Validating before you trust it

Don't treat "the script ran without a traceback" as success:

1. Check the source's own log output for a plausible match/candidate
   count — zero every time across every state usually means a bug, not
   that the state genuinely has none.
2. Confirm the new column(s) exist in `outputs/csv/top_candidates_<st>.csv`
   even on a run with few/zero matches (this is exactly the failure mode
   the pre-init fix above prevents — verify it actually works, don't
   just add the line and assume).
3. If it's a candidate source, check the dedup priority did what you
   expected — a `combined['source'].value_counts()` print right before
   and after the dedup step shows whether your source's candidates
   mostly got absorbed into existing ones (fine) or mostly survived as
   new sites (also fine, just confirm it's the outcome you intended).
4. Spot-check a few matched sites against the source's real underlying
   data (a facility name, an address) — a plausible-looking match can
   still be wrong if a coordinate transform or radius unit is off.

## Checklist

- [ ] Decided: candidate source or corroboration source
- [ ] Emits/matches using the exact common schema column names
- [ ] Wrapped in try/except with a graceful empty-result fallback
- [ ] Manual-download sources print clear instructions when the file is missing
- [ ] (Candidate sources) Added to the dedup priority dict, in `all_frames`, and in the priority print statement
- [ ] (Corroboration sources) New column pre-initialized before the match loop, not just inside it
- [ ] New column added to `EXPORT_COLS` in `score_and_export.py` (or `fetch_texas_parcels.py` for Texas)
- [ ] Ported to each target repo individually, checking that repo's actual variable names and existing sources first
- [ ] Ran the full pipeline per repo and inspected real output, not just exit code
