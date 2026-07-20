# Adding a New State

Two separate phases, in order. Phase 1 happens entirely inside a **new
state repo** — this repo (DCScreenerMap) has no part in it. Phase 2 wires
that finished pipeline's output into the map.

Budget real time for Phase 1: the mechanical renaming is an hour or two,
but finding correct real data sources for a new state (parcel GIS, WARN
Act notices, utility rates) is genuine research, not config.

---

## Phase 1 — Build the state's own pipeline repo

### 1.1 Fork the right template

Fork **WestVirginiaDCScreener**, not Alabama or Tennessee. It's the
newest pipeline: every current source is wired in correctly (EIA860, GEM
Coal Tracker, EPA Redevelopment Mapper, FRS, TRI, OSM, RCRA CA
corroboration) and it has no known bugs. Forking an older repo means
inheriting bugs that were already found and fixed elsewhere — this
happened with Kentucky, which was forked before several of these fixes
existed and needed a large catch-up pass (see "Known traps" below).

Rename the repo itself (`NewStateDCScreener`) and clone it locally.

### 1.2 Rename the state-specific files

WV's naming convention — keep it:

| File | Rename to |
|---|---|
| `download_westvirginia.py` | `download_<state>.py` |
| `download_westvirginia_extras.py` | `download_<state>_extras.py` |
| `download_gas_pipelines_wv.py` | `download_gas_pipelines_<st>.py` |
| `fetch_parcels_wv.py` | `fetch_parcels_<st>.py` (only if you end up writing a dedicated parcel script — see 1.4) |

`<state>` = full lowercase name (`westvirginia`), `<st>` = two-letter
postal code lowercase (`wv`). These two forms both appear — check which
one a given filename/variable already uses before assuming.

### 1.3 Update every state-identifying constant

This is the single most bug-prone step in the whole process — Kentucky's
`enrich_columns.py` had `STATE = "tn"` left over from its Tennessee
lineage, which meant that script tried to read a file
(`candidates_enriched_tn.gpkg`) that never existed and could not
possibly have run successfully. Nobody caught it until the pipeline was
actually run end-to-end months later. **Grep, don't eyeball.**

```bash
grep -n 'TARGET_STATES\s*=\|^STATE\s*=\|STATES\s*=\s*\[\|== "WV"\|== .WV.\|"WV"' *.py
```

Fix every hit:
- `build_candidates.py`: `TARGET_STATES = ["WV"]` → your state's postal code
- `download_data.py`: `STATES = ["WV"]` and the `STATE_NAMES` dict (NHD's
  S3 filenames use underscores between words, e.g. `"West_Virginia"`)
- `enrich_columns.py`, `enrich_retirement.py`, `enrich_candidates.py`,
  `fetch_parcels.py`, `filter_pipeline.py`, `score_and_export.py`: each
  has its own `STATE = "wv"` (lowercase two-letter) — these control which
  intermediate `.gpkg`/`.csv` file that stage reads and writes, so a
  stale one doesn't just mislabel output, it silently breaks the whole
  stage or crashes it outright.
- Any `State == "WV"` or `"State='WV'"` filter buried inside a function
  (score_and_export.py's FCC fiber-block query, enrich_columns.py's
  grid-capacity EIA-860 filters, enrich_candidates.py's Google Maps
  query string) — the grep above catches most, but re-run it after your
  first pass since fixing one file's imports can reveal more.

### 1.4 Replace the state-specific data sources

These don't follow a template — every state's GIS landscape is
different. Real research required:

- **Parcel GIS** (owner + acreage). Best case: a single statewide
  ArcGIS FeatureServer, like Kentucky's `opengisdata.ky.gov` or West
  Virginia's WVGIS (query by point, small search-radius fallback loop).
  Worst case: no statewide service, and you build a per-county
  `COUNTY_SERVICES` dict like Tennessee's `enrich_columns.py` does for
  its handful of metro counties, accepting that most rural counties will
  have no coverage. Write the result to `current_owner` / `owner_source`
  / `parcel_acres` — these exact column names, not `parcel_owner` or
  anything else (Kentucky's `fetch_parcels_ky.py` used the wrong name
  and silently lost owner data for its entire history until this was
  caught).
- **WARN Act layoff notices**: check whether the state's labor/workforce
  agency has a stable bulk-download feed. As of this writing, no state
  in this project has one — every `enrich_retirement.py` silently skips
  this signal. Don't assume it's unfixable without checking fresh; agency
  websites change.
- **State environmental agency feeds** (if the state has something like
  Tennessee's ACRES/SEMS pull or Alabama's RCRA inactive list).
- **Utility rate / market context** for `score_and_export.py`'s
  `STATE_SCORE` dict — real cents/kWh figures and the utilities that set
  them, not guessed. Kentucky's is a good example of the level of detail
  expected: `"KY": 13, # LG&E/KU cheap power, no income tax, Louisville/Lex markets ~3.8-4.2¢/kWh, AEP KY ~4.5¢, TVA east KY`.
- **County/FIPS-scoped filters** inside `download_<state>.py` — census
  tract GEOID prefixes, county FIPS ranges for BLS LAUS series IDs, etc.
  Search for the old state's FIPS code as a literal string
  (`grep -n '"54"' download_westvirginia.py`, WV's FIPS) since these are
  easy to miss when they're embedded in a larger string.

Leave the multi-state sources alone — EIA860, GEM Coal Tracker, EPA
Redevelopment Mapper, FRS, TRI, and OSM are already generically filtered
by `TARGET_STATES` and need no per-state code changes.

### 1.5 Get the raw data downloaded

```bash
python3 download_data.py              # national datasets, ~1-2GB
python3 download_<state>.py           # state-specific datasets
python3 download_<state>_extras.py    # hazard/environment datasets
python3 download_gas_pipelines_<st>.py
```

Budget 15–30 minutes depending on connection speed for the first run;
re-runs skip files that already exist. If a source 404s, check whether
it's a genuinely dead upstream URL before assuming your code is wrong —
this has happened three times already in this project family (EIA's
`ElectricRetail_Territories.zip`, a PAD-US 4.1 ScienceBase URL, and
Kentucky's statewide parcel FeatureServer). All three fail gracefully
inside existing try/except blocks; the pipeline runs fine without that
one signal.

### 1.6 Run the full pipeline and actually check the output

```bash
python3 build_candidates.py
python3 filter_pipeline.py
python3 fetch_epa_compliance.py
python3 enrich_retirement.py
python3 fetch_parcels_<st>.py         # or fetch_parcels.py, whichever you kept
python3 enrich_columns.py
python3 score_and_export.py
python3 check_adjacent_land.py
```

Don't treat a clean exit code as success. Actually check:
- Candidate counts at each stage look plausible (not zero, not
  suspiciously identical to some other state's numbers)
- `outputs/csv/top_candidates_<st>.csv` has `current_owner`/`parcel_acres`
  populated for at least some sites, not silently empty for all 62 rows
- `acres_source` and `rcra_corrective_action` columns exist in the output
  even if zero rows are populated — if they're missing entirely, check
  `EXPORT_COLS` in `score_and_export.py` includes them AND that the
  column is pre-initialized before use in `enrich_columns.py` (`if "col"
  not in cands.columns: cands["col"] = ""`) — a column only ever assigned
  conditionally inside a loop silently vanishes from the export on a run
  with zero matches
- Spot-check a handful of `Street_Address`/`City`/county values on a map
  — wrong-state contamination shows up here first

Write a `run_full_pipeline.sh` (see any other state repo's for the
pattern) once you've confirmed the real stage order — don't assume it
matches another state's; Alabama's has a different stage list than
Tennessee's (no `fetch_epa_compliance.py`, uses `enrich_candidates.py` +
`fetch_parcels.py` instead), and this exact mismatch caused a run to
crash immediately when copied blind.

### 1.7 Write the state's own README

Follow the structure of any recently-written one (Kentucky or West
Virginia) — pipeline architecture diagram, "Why \<State\>" market
section grounded in real numbers (not assumed), data sources table,
setup/run instructions matching what you actually verified in 1.6.

### Known traps (found the hard way, across TN/VA/WV/MS/ND/LA/AL/TX/KY)

- Fork-lineage naming leftovers in comments/print statements (a script
  that prints "(AL)" while correctly processing Kentucky data) are
  usually harmless — verify what the code *does*, not what it says,
  before spending time "fixing" a label.
- But a `STATE = "wv"`-style variable that controls a file path is never
  harmless — it either crashes the stage or silently processes/writes
  the wrong file. Always verify these by running the code, not by
  reading it.
- A hardcoded output filename from the fork source (`top_candidates_al.csv`
  instead of `top_candidates_<st>.csv`) will crash whatever stage reads
  it — `check_adjacent_land.py` is a repeat offender across multiple
  forks.

---

## Phase 2 — Wire the finished pipeline into this map

Only start this once Phase 1's `top_candidates_<st>.csv` is real,
verified data.

1. Write `scripts/extract_<st>.py` in **this** repo. Copy an existing one
   (`extract_va.py` is a clean, recent example) and adapt: it reads that
   state's CSV directly from its own repo's local checkout on disk,
   converts to the common site schema (`state`, `name`, `county`, `city`,
   `lat`, `lon`, `score`, `acres`, `owner`, `conf`, `type`, `rank`), and
   writes `data/sites_<st>.json`. Watch for state-specific quirks in the
   county field — Virginia's independent cities needed special handling
   because some share a name with a legally distinct county.
2. `python3 scripts/merge_sites.py <st>` — folds the new state into the
   combined `data/sites.json`. Replaces, never appends, so safe to
   re-run.
3. Add the new state to `STATE_META` in `scripts/build_map.py` — display
   name, bounding box, and a **genuinely new** categorical color. The
   current 8-slot CVD-safe palette (blue, aqua, yellow, green, violet,
   red, magenta, orange) is fully used; picking a 9th color means
   choosing and validating a new one the same way the `dataviz` skill's
   reference palette was validated (`scripts/validate_palette.js` from
   that skill, run against candidate orderings) — not an arbitrary or
   cycled reuse of an existing slot.
4. `python3 scripts/build_map.py && python3 scripts/gen_map_html.py`
5. Open `index.html` locally (`python3 -m http.server` in this
   directory) and verify the new state's markers, info panel, and table
   rows render correctly before republishing the Artifact.

## Checklist

- [ ] Forked WestVirginiaDCScreener (not an older template)
- [ ] All state-identifying constants updated and re-grepped for leftovers
- [ ] Parcel GIS source found and writes to `current_owner`/`owner_source`/`parcel_acres`
- [ ] WARN Act feed checked (even if still unavailable)
- [ ] `STATE_SCORE` entry has real, cited utility rate figures
- [ ] Full pipeline run end-to-end with output actually inspected, not just exit code
- [ ] `run_full_pipeline.sh` written and matches the real, verified stage order
- [ ] State's own README written
- [ ] `scripts/extract_<st>.py` written in DCScreenerMap
- [ ] New color validated and added to `STATE_META`
- [ ] `index.html` regenerated and checked locally before publishing
