# DCScreenerMap

Combined interactive map visualizing brownfield data center screening results
across all states covered by the DCScreener pipeline family:
[TennesseeDCScreener](https://github.com/Arthurfok1/TennesseeDCScreener),
[MississippiDCScreener](https://github.com/Arthurfok1/MississippiDCScreener),
[NorthDakotaDCScreener](https://github.com/Arthurfok1/NorthDakotaDCScreener),
[KentuckyDCScreener](https://github.com/Arthurfok1/KentuckyDCScreener),
[AlabamaDCScreener](https://github.com/Arthurfok1/AlabamaDCScreener),
[DataCenterScreener](https://github.com/Arthurfok1/DataCenterScreener) (Texas),
[LouisianaDCScreener](https://github.com/Arthurfok1/LouisianaDCScreener), and
[VirginiaDCScreener](https://github.com/Arthurfok1/VirginiaDCScreener).

`index.html` is a single self-contained page — a custom SVG-based US map (no
external map tiles or network requests) with a candidate-site table view,
per-site info panel, state-colored markers, real river geometry, and major
population centers for orientation. It currently covers 340 sites across all
8 states (KY 62, VA 57, AL 56, TX 49, TN 42, LA 41, MS 30, ND 3) — all 8
slots of the project's categorical palette are now in use. (Site counts
change whenever a state repo's pipeline is re-run and its data re-extracted
here — see "Picking Up This Project" below for how that flow works.)

Click a state (on the map or in the sidebar list) to jump-zoom to it, or
scroll/drag to zoom and pan freely; site markers shrink as you zoom in so
individual sites stay visually distinct instead of merging into overlapping
blobs, and a scale bar (bottom-right) shows real distance at the current
zoom level.

## Picking Up This Project

Read this first if you're new here — it explains the whole project family,
not just this one repo, so you can navigate confidently before diving into
code.

### The big picture

This repo doesn't generate any site data itself. It's the aggregator and
viewer for 8 independent, state-specific pipelines that each screen retired
industrial sites (closed power plants, factories, mills) for suitability as
behind-the-meter data center campuses — meaning sites with existing
grid/gas infrastructure that could host on-site generation for a large
compute load. Each state's pipeline is its own GitHub repo with its own
multi-stage data pipeline; this repo's only job is to pull each state's
*already-ranked* CSV output, convert it to a shared schema, and render all
8 states together on one interactive map.

The live map is published as a Claude Artifact — republishing it after a
data refresh is a manual step (see below), not automatic. It's private by
default; the owner needs to share it from the Artifact page in Claude if
someone outside the account needs the link.

### The 8 state repos

| State | Repo | Sites (as of last refresh) |
|---|---|---|
| Tennessee | [TennesseeDCScreener](https://github.com/Arthurfok1/TennesseeDCScreener) | 42 |
| Virginia | [VirginiaDCScreener](https://github.com/Arthurfok1/VirginiaDCScreener) | 57 |
| Louisiana | [LouisianaDCScreener](https://github.com/Arthurfok1/LouisianaDCScreener) | 41 |
| North Dakota | [NorthDakotaDCScreener](https://github.com/Arthurfok1/NorthDakotaDCScreener) | 3 |
| Mississippi | [MississippiDCScreener](https://github.com/Arthurfok1/MississippiDCScreener) | 30 |
| Kentucky | [KentuckyDCScreener](https://github.com/Arthurfok1/KentuckyDCScreener) | 62 |
| Alabama | [AlabamaDCScreener](https://github.com/Arthurfok1/AlabamaDCScreener) | 56 |
| Texas | [DataCenterScreener](https://github.com/Arthurfok1/DataCenterScreener) | 49 |

**Lineage matters for understanding the code you'll find in these repos.**
Alabama was the *original* pipeline. Tennessee was forked from Alabama, and
every other state was in turn forked from Tennessee. That history is why
you'll see naming oddities scattered through several state repos — file
paths, CSV filenames, or print statements that still say `_al` (Alabama) or
"Tennessee" inside a completely different state's code. These have been
checked and are cosmetic leftovers from the fork history, not functional
bugs — safe to leave alone unless you're specifically doing cleanup. If you
do find one you're unsure about, verify what the code actually *does*
before assuming the label is meaningful; several past "obviously wrong"
labels turned out to be self-consistent (a script that both writes and
reads a confusingly-named file) rather than broken.

### How a state's data reaches this map

1. A state repo's pipeline runs through several stages — download raw data,
   build a candidate pool, apply spatial filters (transmission proximity,
   gas pipeline distance, flood zones, etc.), score retirement confidence,
   enrich with parcel/ownership data, then score and export. The end
   result is `outputs/csv/top_candidates_<state>.csv` in that state's own
   repo, plus a `.geojson` twin.
2. This repo has one `scripts/extract_<state>.py` per state (see
   "Structure" below for which ones exist). Each reads that CSV directly
   from the state repo's local checkout on disk and converts it to this
   project's common site schema, writing `data/sites_<state>.json`.
3. `scripts/merge_sites.py` folds one or more of those per-state files
   into the combined `data/sites.json` — replacing that state's old
   entries, never appending, so it's always safe to re-run.
   `data/sites.json` is what every other script actually reads from; the
   per-state `sites_<state>.json` files are just an intermediate step.
4. `scripts/build_map.py` combines `data/sites.json` with each state's
   metadata (display name, bounding box, categorical color) into
   `data/map_payload.json`, which `scripts/gen_map_html.py` embeds into
   `index.html`.
5. `index.html` gets republished to the live Artifact URL.

### Refreshing a state's data

Whenever a state repo's pipeline gets re-run — new upstream data, a bug
fix, a new enrichment source — bring the map up to date:

```bash
# 1. Re-run that state's own pipeline in its own repo, through score_and_export.py
# 2. Then, from this repo (DCScreenerMap/):
python3 scripts/extract_<state>.py     # re-reads that state's latest CSV
python3 scripts/merge_sites.py <state> # folds it into the combined data/sites.json
python3 scripts/build_map.py
python3 scripts/gen_map_html.py
```

`merge_sites.py` also accepts multiple states in one call (e.g.
`python3 scripts/merge_sites.py va la tn`) if you're refreshing several at
once.

Open the regenerated `index.html` locally (`python3 -m http.server` in this
directory, then visit it in a browser) and sanity-check the state's
markers, info panel, and table rows before republishing the Artifact.

### Adding a brand-new state

Two separate things have to happen, in this order, and this repo only
covers the second one:

1. **Build that state's own screening pipeline repo first** — see
   "Building a brand-new state pipeline" below. This repo has no part in
   that; it only ever reads a finished `top_candidates_*.csv`.
2. Once that pipeline produces a ranked CSV, wire it into the map: write
   an extractor, give it the next unused color slot in `STATE_META` (see
   "Color palette" below — the palette is currently full), rebuild. See
   "Adding a new state" below for the exact steps.

### Building a brand-new state pipeline

This is the bigger lift and happens entirely inside a new state repo, not
here. Fork **WestVirginiaDCScreener**, not Alabama or Tennessee — it's the
newest pipeline, has every current source wired in correctly (EIA860, GEM
Coal Tracker, EPA Redevelopment Mapper, FRS, TRI, OSM, RCRA CA
corroboration) and no known bugs, so it's the cleanest starting point
rather than something forked years ago that later got patched piecemeal.
After forking:

1. Swap every state-specific constant: `TARGET_STATES`, FIPS code, county
   list, state postal abbreviation used in file paths and CSV names.
2. Replace the state-specific data sources — county/statewide parcel GIS
   endpoint, any state environmental agency feeds — with that state's
   real equivalents. These do not follow a template; each state's GIS
   landscape is different (see e.g. Tennessee's README "County GIS Parcel
   Coverage" table for what this looks like once done).
3. Leave the multi-state sources alone (EIA860, GEM Coal Tracker, EPA
   Redevelopment Mapper, FRS, TRI, OSM, RCRA CA) — they're already
   state-filtered generically by `TARGET_STATES` and need no per-state
   code.
4. Run the full pipeline end to end and sanity-check the output CSV
   (site count, score distribution, spot-check a few `Street_Address`
   values on a map) before treating it as real.
5. Update that repo's own README's "Data Sources" table — the map-level
   handoff above assumes each state repo documents its own sourcing.

### Adding a new brownfield source to an existing state's pipeline

Every state's `build_candidates.py` follows the same pattern: a numbered
list of sources (currently 1 EIA860, 1b GEM Coal Tracker, 2 FRS, 3 TRI,
4 OSM, 5 EPA Redevelopment Mapper — TRI is absent in Alabama and Texas),
each producing rows in the shared candidate schema (`source`, `site_id`,
`Plant_Name`, `State`, `County`, `Latitude`, `Longitude`, etc.), followed
by a single dedup pass keyed on 500m spatial proximity that picks one row
per cluster using a priority order defined near the bottom of the file
(e.g. `{"EIA860": 0, "GEM_COAL": 1, "SRP_REDEV_MAPPER": 2, "FRS": 3,
"TRI": 4, "OSM": 5}` — lower number wins). To add a new source:

1. Add a new numbered block in `build_candidates.py` that queries/reads
   the new dataset and emits rows in the common schema, tagged with a
   distinct `source` value.
2. Add that `source` value to the priority dict, choosing its rank based
   on how trustworthy/precise the new dataset's coordinates and site
   identity are relative to the existing sources.
3. If the source needs a manually-downloaded file (no stable bulk API —
   GEM's Coal Plant Tracker is the existing example), have the script
   glob-match a versioned filename pattern in a dedicated subfolder under
   `data/<state>/raw/`, and print clear instructions (source URL, exact
   destination folder, filename pattern) when the file is missing instead
   of failing silently. Look at the GEM block in any state's
   `build_candidates.py` (search for `Source 1b`) as the template.
4. If the source adds any new enrichment column downstream (in
   `enrich_columns.py` / `fetch_texas_parcels.py` for Texas), remember to
   add that column name to `EXPORT_COLS` in `score_and_export.py` —
   **this is easy to miss** and the column will be computed correctly but
   silently dropped from the final CSV without an error. This exact bug
   happened with `acres_source` and `rcra_corrective_action` during this
   handoff and was only caught by running the full pipeline and checking
   real output, not by any smoke test.
5. Port the new source to the other state repos individually — there is
   no shared library between repos, each `build_candidates.py` is a full
   copy that needs the same edit applied by hand.

### Known gaps, as of this handoff

- **EPA retirement-signal integration** (each state repo's
  `fetch_epa_compliance.py`, which queries EPA's live ECHO/ICIS-AIR/
  ICIS-NPDES APIs per-site by FRS registry ID) is done for 6 of 8 states —
  Tennessee, Virginia, Louisiana, North Dakota, Mississippi, Kentucky.
  **Alabama and Texas don't have it yet.** Without it, a state's retirement
  confidence skews heavily toward "UNVERIFIED" since the pipeline has no
  real compliance evidence to work with — this was a large, real accuracy
  improvement for the 6 states that got it, and is the natural next task
  if you want consistency across all 8. Each of the 6 done states'
  `fetch_epa_compliance.py` is a good template — the API usage notes in
  its header comment (verified registry-ID query behavior, rate limiting)
  apply identically to Alabama and Texas.
- **WARN Act layoff-notice data is manual-only in every single state** — no
  state employment agency was found to have a stable bulk-download feed,
  so every state's `enrich_retirement.py` silently skips this one signal.
  Not something to "fix" without first checking whether a given state's
  agency has changed its data-access story since this was last checked.
- The categorical color palette is fully used (all 8 slots taken) — see
  "Color palette" below for what a 9th state would need.
- **Three download URLs are confirmed dead as of this handoff** (verified
  via live `curl`, not just inferred): EIA's `ElectricRetail_Territories.zip`
  (`https://www.eia.gov/maps/map_data/ElectricRetail_Territories.zip`, used
  in each state's `download_<state>.py`), the ScienceBase-hosted PAD-US
  4.1 state GDB used by West Virginia's
  `download_westvirginia_extras.py`, and Kentucky's statewide parcel
  FeatureServer (`opengisdata.ky.gov/.../KY_Statewide_Parcel_Boundary`,
  used by `fetch_parcels_ky.py` — a 404, likely means KY's Open Data
  Portal moved or renamed the layer). All three already fail gracefully
  inside existing try/except blocks — the pipeline runs fine without them,
  just missing that one signal — so this is a "known gap to eventually
  fix," not a "pipeline is broken" situation. Re-check for a replacement
  URL before spending time debugging why a related score/column looks
  empty.
- **GEM's Global Coal Plant Tracker requires a one-time manual download**
  per machine/checkout — it's gated behind an email signup form
  (globalenergymonitor.org/projects/global-coal-plant-tracker/download-data/),
  so it can't be automated like the other sources. Each state's
  `build_candidates.py` looks for it in `data/<state>/raw/gem/` and prints
  the exact URL and destination if the file is missing, but a new
  environment (or a fresh clone) will need this done once before Source
  1b produces any candidates — worth doing on day one of onboarding
  rather than discovering it mid-pipeline-run.

## Structure

- `index.html` — the rendered map, generated by `scripts/gen_map_html.py`. This
  is the file to open in a browser or publish as a static page.
- `data/us_states.geojson` — raw US state boundary polygons (source data).
- `data/state_shapes.json` — state boundary polygons reduced/rounded for
  embedding, generated from `us_states.geojson` by `scripts/process_states.py`.
- `data/sites.json` — the merged list of all candidate sites across every
  state, each with `state`, `name`, `county`, `city`, `lat`, `lon`, `score`,
  `acres`, `owner`, `conf`, `type`, `rank`.
- `data/map_payload.json` — `sites.json` + per-state metadata (display name,
  bounding box, categorical color) combined into the single payload embedded
  in `index.html`, generated by `scripts/build_map.py`.
- `data/rivers.json` — real named-river line geometry (23 rivers, e.g.
  Mississippi, Tennessee, Cumberland, James-of-North-Dakota, Rio Grande) for
  the 8 covered states, generated from Natural Earth's 10m rivers dataset by
  `scripts/process_rivers.py`. Filtered by genuine point-in-polygon
  intersection with the real state shapes, not bounding boxes, to avoid false
  positives (an earlier bbox-only pass wrongly pulled in the St. Lawrence).
  Virginia's James River (through Richmond) isn't in this dataset at 10m
  resolution and isn't hand-drawn as a substitute — see the script's header
  comment.
- `data/cities.json` — hand-curated major population centers (state capital +
  2-5 largest metros per state, 34 total), each with `name`, `state`, `lat`,
  `lon`, `capital`. Not derived from an external source — authored directly,
  same as `STATE_META` in `build_map.py`.
- `scripts/extract_<state>.py` — one per state, each reading that state's own
  `top_candidates_*.csv` (from that state's own repo, not this one) and
  converting it to the common site schema. Present for `tn`, `ms`, `nd`,
  `ky`, `la`, `va`; not yet written for `al` or `tx` (those two states'
  current site data was carried over from an earlier one-off extraction —
  see "Picking Up This Project" below).
- `scripts/merge_sites.py <state> [<state> ...]` — folds one or more
  `data/sites_<state>.json` files into the combined `data/sites.json`,
  replacing (not appending) that state's existing entries.
- `scripts/build_map.py` — merges `data/sites.json` with per-state metadata
  (name, bbox, color) into `data/map_payload.json`.
- `scripts/gen_map_html.py` — embeds `map_payload.json`, `state_shapes.json`,
  `rivers.json`, and `cities.json` into the HTML/JS template and writes
  `index.html`.
- `scripts/process_states.py` — regenerates `data/state_shapes.json` from
  `data/us_states.geojson`.
- `scripts/process_rivers.py` — downloads Natural Earth's rivers dataset into
  the gitignored `data/raw/` cache and regenerates `data/rivers.json`.
  Requires `requests` (see `requirements.txt`).

## Adding a new state

1. Run that state's screener pipeline through to `top_candidates_*.csv`.
2. Write (or adapt an existing `extract_<state>.py` into) a small script
   that reads the CSV and writes `data/sites_<state>.json` in the common
   site schema.
3. Run `python3 scripts/merge_sites.py <state>` to fold it into
   `data/sites.json`.
4. Add the new state's abbreviation to `STATE_META` in `scripts/build_map.py`,
   assigning the next unused color slot in the project's fixed 8-slot
   categorical palette (see the `dataviz` skill's `references/palette.md`) —
   never an arbitrary or cycled color.
5. Run `python3 scripts/build_map.py && python3 scripts/gen_map_html.py`.
6. Open `index.html` locally (or via `python3 -m http.server`) and verify the
   new state's markers, info panel, and table rows render correctly before
   republishing.

## Color palette

State marker colors are assigned in the fixed CVD-safe categorical order from
the `dataviz` skill (blue, aqua, yellow, green, violet, red, magenta, orange —
all 8 slots now in use). The palette has no 9th slot: a state added beyond
these 8 needs a genuinely new categorical color chosen and validated the same
way the `dataviz` skill's reference palette was (run
`scripts/validate_palette.js` from that skill against candidate orderings),
not an arbitrary or cycled reuse of an existing slot.
