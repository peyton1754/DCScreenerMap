import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(REPO_ROOT, 'data', 'map_payload.json')) as f:
    payload = json.load(f)
with open(os.path.join(REPO_ROOT, 'data', 'state_shapes.json')) as f:
    shapes = json.load(f)

payload['shapes'] = shapes

# Safe embedding: prevent premature </script> termination
data_json = json.dumps(payload).replace("</", "<\\/")

HTML = """<meta charset="utf-8">
<title>Data Center Site Screener — Multi-State Map</title>
<meta name="description" content="Scored brownfield candidate sites across state pipelines, plotted on a real US map.">

<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  .viz-root {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #0a0a0a; color: #e0e0e0;
    position: relative; width: 100%; min-height: 100vh; overflow: hidden;
  }
  .map-stage { position: relative; width: 100%; height: 100vh; min-height: 640px; }
  svg#mapSvg { width: 100%; height: 100%; display: block; background: #0a0a0a; overflow: hidden; cursor: grab; touch-action: none; }

  .panel {
    position: absolute; z-index: 10;
    background: rgba(15,15,20,0.95); color: #e0e0e0;
    border-radius: 8px; border: 1px solid #333;
    font-size: 12px; line-height: 1.5;
  }
  .filters { top: 14px; left: 14px; padding: 12px 16px; width: 200px; max-height: calc(100vh - 300px); overflow-y: auto; }
  .filters strong { display: block; margin-bottom: 6px; color: #fff; font-size: 13px; }
  .search-wrap { position: relative; }
  .search-wrap input[type=text] {
    width: 100%; font-family: inherit; font-size: 12.5px; padding: 7px 26px 7px 8px;
    background: #141414; color: #e0e0e0; border: 1px solid #333; border-radius: 6px;
  }
  .search-wrap input[type=text]:focus { outline: none; border-color: #3987e5; }
  .search-wrap input[type=text]::placeholder { color: #666; }
  .search-wrap button {
    position: absolute; right: 3px; top: 50%; transform: translateY(-50%);
    width: 20px; height: 20px; border: none; background: transparent; color: #666;
    font-size: 15px; cursor: pointer; display: none; line-height: 1;
  }
  .search-wrap button:hover { color: #fff; }
  .search-wrap.has-query button { display: block; }
  .search-count { font-size: 11px; color: #666; margin-top: 4px; min-height: 14px; }
  .filters label { display: flex; align-items: center; gap: 7px; margin: 5px 0; cursor: pointer; }
  .filters .swatch { width: 10px; height: 10px; border-radius: 50%; flex: none; }
  .filters .n { color: #666; margin-left: auto; font-variant-numeric: tabular-nums; }
  .filters hr { border: none; border-top: 1px solid #333; margin: 10px 0; }
  .filters input[type=range] { width: 100%; margin-top: 6px; accent-color: #3987e5; }
  .filters .score-val { color: #888; float: right; }
  .filters .view-btns { display: flex; gap: 6px; margin-top: 10px; }
  .filters .view-btns button {
    flex: 1; font-size: 11.5px; padding: 5px 0; border-radius: 5px; border: 1px solid #333;
    background: #1a1a1a; color: #999; cursor: pointer;
  }
  .filters .view-btns button.active { background: #3987e5; color: #fff; border-color: #3987e5; }
  .filters label .zoomable:hover { color: #fff; text-decoration: underline; }
  .zoom-indicator {
    display: none; align-items: center; justify-content: space-between;
    background: #1a1a1a; border: 1px solid #333; border-radius: 6px;
    padding: 6px 10px; margin-bottom: 8px; font-size: 11.5px; color: #ccc;
  }
  .zoom-indicator.show { display: flex; }
  .zoom-indicator button {
    background: none; border: none; color: #5b9dd9; cursor: pointer; font-size: 11.5px; padding: 0;
  }
  .zoom-indicator button:hover { color: #7fb4ec; text-decoration: underline; }

  .legend { bottom: 20px; left: 14px; padding: 12px 16px; }
  .legend strong { display: block; margin-bottom: 6px; color: #fff; font-size: 13px; }
  .legend-item { display: flex; align-items: center; margin: 4px 0; }
  .legend-dot { width: 12px; height: 12px; border-radius: 50%; margin-right: 8px; border: 2px solid rgba(255,255,255,0.3); flex: none; }
  .legend-size { display: flex; align-items: center; gap: 8px; margin-top: 8px; padding-top: 8px; border-top: 1px solid #333; color: #888; font-size: 11px; }
  .legend-size .sd { border-radius: 50%; background: #888; flex: none; }

  .info-panel {
    top: 14px; right: 14px; padding: 16px; width: 340px; max-height: calc(100vh - 28px);
    overflow-y: auto;
  }
  .info-panel h2 { font-size: 16px; margin-bottom: 8px; color: #fff; }
  .info-panel h3 { font-size: 12px; color: #999; margin: 12px 0 4px; text-transform: uppercase; letter-spacing: 0.5px; }
  .info-panel .placeholder { color: #888; margin: 8px 0; }
  .info-panel .sub { color: #666; font-size: 11px; }
  .field { display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px solid #1a1a1a; gap: 10px; }
  .field .label { color: #888; flex: none; }
  .field .value { color: #e0e0e0; text-align: right; }
  .confidence { display: inline-block; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 12px; }
  .conf-HIGH { background: #1a472a; color: #4ade80; }
  .conf-MEDIUM { background: #3b3a15; color: #facc15; }
  .conf-LOW { background: #3b2a15; color: #fb923c; }
  .conf-ACTIVE_WARNING { background: #4a1515; color: #f87171; }
  .conf-UNVERIFIED { background: #2a2a2a; color: #999; }
  .score-bar { height: 6px; border-radius: 3px; background: #1a1a1a; margin: 6px 0; }
  .score-bar .fill { height: 100%; border-radius: 3px; }
  .state-pill { display: inline-flex; align-items: center; gap: 5px; font-size: 11.5px; color: #999; margin-left: 8px; }
  .state-pill .dot { width: 8px; height: 8px; border-radius: 50%; }
  .notes-box {
    width: 100%; min-height: 70px; resize: vertical; font-family: inherit; font-size: 12.5px;
    background: #141414; color: #e0e0e0; border: 1px solid #333; border-radius: 6px;
    padding: 8px; line-height: 1.5;
  }
  .notes-box:focus { outline: none; border-color: #3987e5; }
  .notes-box::placeholder { color: #666; }
  .notes-saved { display: block; text-align: right; font-size: 10.5px; color: #4ade80; margin-top: 3px; opacity: 0; transition: opacity 0.2s; }
  .notes-saved.show { opacity: 1; }

  .stats-bar { bottom: 20px; right: 14px; padding: 10px 16px; }

  .scale-bar { bottom: 62px; right: 14px; padding: 6px 12px; display: flex; align-items: center; gap: 8px; }
  .scale-bar-line { height: 0; border-top: 2px solid #ccc; position: relative; width: 0; }
  .scale-bar-line::before, .scale-bar-line::after {
    content: ''; position: absolute; top: -4px; width: 0; height: 8px; border-left: 1px solid #ccc;
  }
  .scale-bar-line::before { left: 0; }
  .scale-bar-line::after { right: 0; }
  .scale-bar-label { font-size: 11px; color: #ccc; white-space: nowrap; }

  .hover-tip {
    position: absolute; z-index: 20; pointer-events: none;
    background: rgba(15,15,20,0.97); color: #e0e0e0; border: 1px solid #333; border-radius: 5px;
    padding: 4px 8px; font-size: 11.5px; white-space: nowrap; opacity: 0; transition: opacity 0.08s;
  }
  .hover-tip.show { opacity: 1; }

  .dot { cursor: pointer; }
  .dot-hit { fill: transparent; cursor: pointer; }
  .state-shape { stroke: #2a2a2a; stroke-width: 1; fill: #131313; cursor: default; }
  .state-highlight { stroke-width: 1.3; cursor: default; }
  .state-highlight.zoomable-state { cursor: pointer; }
  .state-highlight.zoomable-state:hover { stroke-width: 2.4; }
  .state-name-label { fill: #666; font-size: 10px; pointer-events: none; text-anchor: middle; }

  .table-panel {
    position: absolute; inset: 0; z-index: 15; background: #0a0a0a;
    display: none; padding: 70px 14px 14px;
  }
  .table-toolbar { position: absolute; top: 14px; left: 14px; right: 14px; z-index: 16; display: flex; align-items: center; }
  .table-toolbar button {
    font-size: 12.5px; padding: 7px 14px; border-radius: 7px; border: 1px solid #333;
    background: #1a1a1a; color: #e0e0e0; cursor: pointer; display: flex; align-items: center; gap: 6px;
  }
  .table-toolbar button:hover { background: #232323; border-color: #444; }
  .table-toolbar .count { margin-left: auto; color: #888; font-size: 12px; }
  .table-wrap { max-height: 100%; overflow: auto; border: 1px solid #333; border-radius: 8px; }
  table.data-table { width: 100%; border-collapse: collapse; font-size: 12.5px; background: rgba(15,15,20,0.95); color: #e0e0e0; }
  table.data-table th, table.data-table td { padding: 8px 10px; text-align: left; border-bottom: 1px solid #1a1a1a; white-space: nowrap; color: #e0e0e0; }
  table.data-table th { position: sticky; top: 0; background: #141414; color: #999; font-weight: 600; cursor: pointer; user-select: none; }
  table.data-table th:hover { color: #fff; }
  table.data-table td.num { font-variant-numeric: tabular-nums; text-align: right; }
  table.data-table tbody tr:hover { background: rgba(255,255,255,0.04); }
  .state-tag { display: inline-flex; align-items: center; gap: 5px; }
  .state-tag .dot { width: 8px; height: 8px; border-radius: 50%; }
</style>

<div class="viz-root">
  <div class="map-stage">
    <svg id="mapSvg" viewBox="0 0 1400 800" preserveAspectRatio="xMidYMid meet"></svg>

    <div class="panel filters" id="filters">
      <div class="search-wrap">
        <input type="text" id="searchBox" placeholder="Search sites, county, owner…" autocomplete="off">
        <button id="searchClear" title="Clear search">&times;</button>
      </div>
      <div class="search-count" id="searchCount"></div>
      <hr>
      <strong>States</strong>
      <div class="zoom-indicator" id="zoomIndicator">
        <span id="zoomLabel"></span>
        <button id="zoomResetBtn">&times; Reset</button>
      </div>
      <div id="stateChips"></div>
      <hr>
      <label style="color:#888">Min score: <span class="score-val" id="scoreVal">0</span></label>
      <input type="range" id="scoreSlider" min="0" max="100" value="0" step="5">
      <div class="view-btns">
        <button id="zoomOutBtn" title="Zoom out">&minus;</button>
        <button id="zoomInBtn" title="Zoom in">+</button>
      </div>
      <div style="font-size:10px;color:#666;margin-top:3px;">Click a state, scroll, or drag to zoom</div>
      <div class="view-btns" style="margin-top:8px;">
        <button id="btnMap" class="active">Map</button>
        <button id="btnTable">Table</button>
      </div>
    </div>

    <div class="panel legend">
      <strong>States</strong>
      <div id="legendItems"></div>
      <div class="legend-size">
        <span>Size = score:</span>
        <span class="sd" style="width:7px;height:7px"></span>
        <span class="sd" style="width:11px;height:11px"></span>
        <span class="sd" style="width:16px;height:16px"></span>
      </div>
    </div>

    <div class="panel info-panel" id="infoPanel">
      <h2>Multi-State Site Screener</h2>
      <p class="placeholder">Click a site to view details.</p>
      <p class="sub">__SITE_COUNT__ scored candidates &bull; __STATE_COUNT__ state pipelines</p>
      <p class="sub"><a href="https://github.com/Arthurfok1/DCScreenerMap" target="_blank" rel="noopener" style="color:#5b9dd9;">Source &amp; data on GitHub &#8594;</a></p>
    </div>

    <div class="panel scale-bar" id="scaleBar">
      <div class="scale-bar-line" id="scaleBarLine"></div>
      <span class="scale-bar-label" id="scaleBarLabel"></span>
    </div>
    <div class="panel stats-bar" id="statsBar"></div>

    <div class="hover-tip" id="hoverTip"></div>
  </div>

  <div class="table-panel" id="tablePanel">
    <div class="table-toolbar">
      <button id="btnBackToMap">&larr; Map</button>
      <span class="count" id="tableCount"></span>
    </div>
    <div class="table-wrap">
      <table class="data-table" id="dataTable">
        <thead>
          <tr>
            <th data-key="state">State</th>
            <th data-key="name">Site</th>
            <th data-key="county">County</th>
            <th data-key="score" class="num">Score</th>
            <th data-key="acres" class="num">Acres</th>
            <th data-key="conf">Retirement</th>
            <th data-key="type">Type</th>
          </tr>
        </thead>
        <tbody id="tableBody"></tbody>
      </table>
    </div>
  </div>
</div>

<script>
const DATA = __DATA_JSON__;

const svg = document.getElementById('mapSvg');
const hoverTip = document.getElementById('hoverTip');
const stateChips = document.getElementById('stateChips');
const legendItems = document.getElementById('legendItems');
const scoreSlider = document.getElementById('scoreSlider');
const scoreVal = document.getElementById('scoreVal');
const infoPanel = document.getElementById('infoPanel');
const statsBar = document.getElementById('statsBar');

const VB_W = 1400, VB_H = 800;
const pipelineKeys = Object.keys(DATA.states);
let visible = new Set(pipelineKeys);
let minScore = 0;
let searchQuery = '';
let pinned = null;

function matchesFilters(s) {
  if (!visible.has(s.state)) return false;
  if (s.score != null && s.score < minScore) return false;
  if (searchQuery) {
    const hay = (s.name + ' ' + s.county + ' ' + s.city + ' ' + s.owner + ' ' + s.type).toLowerCase();
    if (!hay.includes(searchQuery)) return false;
  }
  return true;
}

// ---- fixed continental-US projection (computed once from real shape data) ----
let US_BBOX = [1e9, 1e9, -1e9, -1e9];
Object.values(DATA.shapes).forEach(s => {
  s.rings.forEach(ring => ring.forEach(([lon, lat]) => {
    US_BBOX[0] = Math.min(US_BBOX[0], lon); US_BBOX[2] = Math.max(US_BBOX[2], lon);
    US_BBOX[1] = Math.min(US_BBOX[1], lat); US_BBOX[3] = Math.max(US_BBOX[3], lat);
  }));
});
function makeProjector(bbox, pad) {
  const [minLon, minLat, maxLon, maxLat] = bbox;
  const cLat = (minLat + maxLat) / 2;
  const xScale = Math.cos(cLat * Math.PI / 180);
  const w0 = (maxLon - minLon) * xScale;
  const h0 = (maxLat - minLat);
  const availW = VB_W - pad*2, availH = VB_H - pad*2;
  const scale = Math.min(availW / w0, availH / h0);
  const drawW = w0 * scale, drawH = h0 * scale;
  const offX = pad + (availW - drawW)/2;
  const offY = pad + (availH - drawH)/2;
  const projFn = function(lon, lat) {
    return [offX + (lon - minLon) * xScale * scale, offY + (maxLat - lat) * scale];
  };
  projFn.scale = scale; // pixels (SVG user units) per degree of latitude — constant across the map
  return projFn;
}
const proj = makeProjector(US_BBOX, 30);

function ringToPath(ring) {
  let d = '';
  ring.forEach(([lon, lat], i) => {
    const [x, y] = proj(lon, lat);
    d += (i === 0 ? 'M' : 'L') + x.toFixed(1) + ',' + y.toFixed(1) + ' ';
  });
  return d + 'Z';
}

const confColor = {
  HIGH: '#4ade80', MEDIUM: '#facc15', LOW: '#fb923c',
  ACTIVE_WARNING: '#f87171', UNVERIFIED: '#999'
};

// ---- build filter chips + legend ----
pipelineKeys.forEach(k => {
  const meta = DATA.states[k];
  const n = DATA.sites.filter(s => s.state === k).length;

  const chip = document.createElement('label');
  const dot = document.createElement('span');
  dot.className = 'swatch';
  dot.style.background = meta.dark;
  const cb = document.createElement('input');
  cb.type = 'checkbox';
  cb.checked = true;
  cb.style.accentColor = meta.dark;
  const txt = document.createElement('span');
  txt.textContent = meta.name;
  txt.className = 'zoomable';
  txt.title = 'Zoom to ' + meta.name;
  const count = document.createElement('span');
  count.className = 'n';
  count.textContent = n;
  chip.appendChild(cb); chip.appendChild(dot); chip.appendChild(txt); chip.appendChild(count);
  chip.addEventListener('click', (e) => {
    e.preventDefault();
    if (visible.has(k) && visible.size === 1) return;
    if (visible.has(k)) { visible.delete(k); cb.checked = false; chip.style.opacity = 0.4; }
    else { visible.add(k); cb.checked = true; chip.style.opacity = 1; }
    render();
  });
  txt.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (currentZoom === k) resetZoom(); else zoomToState(k);
  });
  stateChips.appendChild(chip);

  const li = document.createElement('div');
  li.className = 'legend-item';
  const ld = document.createElement('div');
  ld.className = 'legend-dot';
  ld.style.background = meta.dark;
  const lt = document.createElement('span');
  lt.textContent = meta.name;
  li.appendChild(ld); li.appendChild(lt);
  legendItems.appendChild(li);
});

scoreSlider.addEventListener('input', () => {
  minScore = +scoreSlider.value;
  scoreVal.textContent = minScore;
  render();
});

const searchBox = document.getElementById('searchBox');
const searchWrap = document.querySelector('.search-wrap');
const searchClear = document.getElementById('searchClear');
const searchCount = document.getElementById('searchCount');

function updateSearchCount() {
  if (!searchQuery) { searchCount.textContent = ''; return; }
  const n = DATA.sites.filter(matchesFilters).length;
  searchCount.textContent = n === 0 ? 'No matches' : n + ' match' + (n === 1 ? '' : 'es');
}
searchBox.addEventListener('input', () => {
  searchQuery = searchBox.value.trim().toLowerCase();
  searchWrap.classList.toggle('has-query', !!searchQuery);
  updateSearchCount();
  render();
});
searchClear.addEventListener('click', () => {
  searchBox.value = '';
  searchQuery = '';
  searchWrap.classList.remove('has-query');
  updateSearchCount();
  render();
  searchBox.focus();
});

function radiusFor(score) {
  if (score == null) return 5;
  return Math.max(4, Math.min(15, score / 8));
}
function scoreColor(score) {
  const pct = Math.min((score||0)/100, 1);
  if (pct > 0.7) return '#22c55e';
  if (pct > 0.5) return '#eab308';
  if (pct > 0.3) return '#f97316';
  return '#ef4444';
}

// ---- render US basemap once (static — shapes never move) ----
const ns = 'http://www.w3.org/2000/svg';
const basemapG = document.createElementNS(ns, 'g');
basemapG.id = 'basemap';
Object.entries(DATA.shapes).forEach(([abbr, s]) => {
  const path = document.createElementNS(ns, 'path');
  const d = s.rings.map(ringToPath).join(' ');
  path.setAttribute('d', d);
  path.setAttribute('class', 'state-shape');
  path.dataset.abbr = abbr;
  basemapG.appendChild(path);
});
svg.appendChild(basemapG);

const highlightG = document.createElementNS(ns, 'g');
svg.appendChild(highlightG);
const dotsG = document.createElementNS(ns, 'g');
svg.appendChild(dotsG);

function render() {
  // highlight the 6 pipeline states (colored fill+stroke when checked, muted when unchecked)
  highlightG.innerHTML = '';
  pipelineKeys.forEach(k => {
    const meta = DATA.states[k];
    const shape = DATA.shapes[k];
    if (!shape) return;
    const on = visible.has(k);
    const path = document.createElementNS(ns, 'path');
    const d = shape.rings.map(ringToPath).join(' ');
    path.setAttribute('d', d);
    path.setAttribute('class', 'state-highlight zoomable-state');
    path.setAttribute('fill', on ? meta.dark : '#131313');
    path.setAttribute('fill-opacity', on ? '0.28' : '1');
    path.setAttribute('stroke', on ? meta.dark : '#2a2a2a');
    path.addEventListener('click', () => {
      if (currentZoom === k) resetZoom(); else zoomToState(k);
    });
    highlightG.appendChild(path);
  });

  dotsG.innerHTML = '';
  const filtered = DATA.sites.filter(matchesFilters);
  filtered.forEach(s => {
    const [x,y] = proj(s.lon, s.lat);
    const color = DATA.states[s.state].dark;
    const scoreAttr = s.score != null ? s.score : '';

    const dot = document.createElementNS(ns, 'circle');
    dot.setAttribute('cx', x); dot.setAttribute('cy', y);
    dot.dataset.score = scoreAttr;
    dot.setAttribute('fill', color);
    dot.setAttribute('stroke', '#fff'); dot.setAttribute('stroke-width', '1.3');
    dot.setAttribute('fill-opacity', '0.85'); dot.setAttribute('stroke-opacity', '0.8');
    dot.setAttribute('class', 'dot');
    dotsG.appendChild(dot);

    const hit = document.createElementNS(ns, 'circle');
    hit.setAttribute('cx', x); hit.setAttribute('cy', y);
    hit.dataset.score = scoreAttr;
    hit.setAttribute('class', 'dot-hit');
    hit.tabIndex = 0;
    hit.addEventListener('mouseenter', (e) => showHoverTip(e, s));
    hit.addEventListener('mousemove', (e) => positionHoverTip(e));
    hit.addEventListener('mouseleave', hideHoverTip);
    hit.addEventListener('click', () => pinSite(s));
    hit.addEventListener('focus', (e) => showHoverTip(e, s));
    hit.addEventListener('blur', hideHoverTip);
    dotsG.appendChild(hit);
  });
  updateDotSizes();

  updateStats(filtered.length);
}

// ---- state zoom (crops the same fixed projection via viewBox — coordinates never move) ----
const zoomIndicator = document.getElementById('zoomIndicator');
const zoomLabel = document.getElementById('zoomLabel');
const scaleBarLine = document.getElementById('scaleBarLine');
const scaleBarLabel = document.getElementById('scaleBarLabel');
const MILES_PER_DEG_LAT = 69.0;
const NICE_MILES = [1,2,5,10,15,20,25,50,75,100,150,200,250,300,500,750,1000,1500,2000,3000];
const MIN_VB_FRAC = 0.05; // deepest manual zoom: 5% of the full map width
const DOT_SHRINK_EXP = 0.65; // how aggressively dots shrink as you zoom in (0 = never shrink, 1 = constant screen size)
let currentZoom = null;
let vbAnim = null;

function getViewBox() {
  const vb = svg.viewBox.baseVal;
  return [vb.x, vb.y, vb.width, vb.height];
}
function setViewBox(x, y, w, h) {
  svg.setAttribute('viewBox', x.toFixed(2) + ' ' + y.toFixed(2) + ' ' + w.toFixed(2) + ' ' + h.toFixed(2));
}
function clampViewBox(x, y, w, h) {
  const minW = VB_W * MIN_VB_FRAC, minH = VB_H * MIN_VB_FRAC;
  w = Math.min(VB_W, Math.max(minW, w));
  h = Math.min(VB_H, Math.max(minH, h));
  const marginX = VB_W * 0.15, marginY = VB_H * 0.15;
  const minX = -marginX, maxX = VB_W + marginX - w;
  const minY = -marginY, maxY = VB_H + marginY - h;
  x = Math.min(Math.max(x, minX), Math.max(minX, maxX));
  y = Math.min(Math.max(y, minY), Math.max(minY, maxY));
  return [x, y, w, h];
}
function isAtFullView() {
  const vb = getViewBox();
  return Math.abs(vb[0]) < 0.5 && Math.abs(vb[1]) < 0.5 &&
    Math.abs(vb[2] - VB_W) < 0.5 && Math.abs(vb[3] - VB_H) < 0.5;
}
function onViewportChange() {
  updateScaleBar();
  updateDotSizes();
  updateZoomUI();
}
function animateViewBox(target, duration) {
  if (vbAnim) cancelAnimationFrame(vbAnim);
  const start = getViewBox();
  const t0 = performance.now();
  const ease = t => 1 - Math.pow(1 - t, 3);
  function frame(now) {
    const t = Math.min(1, (now - t0) / duration);
    const e = ease(t);
    const cur = start.map((v, i) => v + (target[i] - v) * e);
    setViewBox(cur[0], cur[1], cur[2], cur[3]);
    onViewportChange();
    vbAnim = t < 1 ? requestAnimationFrame(frame) : null;
  }
  vbAnim = requestAnimationFrame(frame);
}
function stateViewBoxTarget(abbr) {
  const [lonMin, latMin, lonMax, latMax] = DATA.states[abbr].bbox;
  const [x0, y1] = proj(lonMin, latMin);
  const [x1, y0] = proj(lonMax, latMax);
  const w = x1 - x0, h = y1 - y0;
  const padX = w * 0.14, padY = h * 0.14;
  return [x0 - padX, y0 - padY, w + padX * 2, h + padY * 2];
}
function zoomToState(abbr) {
  currentZoom = abbr;
  animateViewBox(stateViewBoxTarget(abbr), 500);
  updateZoomUI();
}
function resetZoom() {
  currentZoom = null;
  animateViewBox([0, 0, VB_W, VB_H], 500);
  updateZoomUI();
}
function stepZoom(factor) {
  const vb = getViewBox();
  const cx = vb[0] + vb[2] / 2, cy = vb[1] + vb[3] / 2;
  const newW = vb[2] * factor, newH = vb[3] * factor;
  const [x, y, w, h] = clampViewBox(cx - newW / 2, cy - newH / 2, newW, newH);
  currentZoom = null;
  animateViewBox([x, y, w, h], 250);
  updateZoomUI();
}
function updateZoomUI() {
  const zoomed = !isAtFullView();
  zoomIndicator.classList.toggle('show', zoomed);
  zoomLabel.textContent = currentZoom ? ('Zoomed: ' + DATA.states[currentZoom].name) : (zoomed ? 'Zoomed in' : '');
}
function updateScaleBar() {
  const vb = svg.viewBox.baseVal;
  const rect = svg.getBoundingClientRect();
  if (!rect.width || !vb.width) return;
  const pxPerUnit = rect.width / vb.width;
  const milesPerUnit = MILES_PER_DEG_LAT / proj.scale;
  const targetPx = 110;
  const targetMiles = (targetPx / pxPerUnit) * milesPerUnit;
  let nice = NICE_MILES[0];
  for (const m of NICE_MILES) { if (m <= targetMiles) nice = m; else break; }
  const barPx = (nice / milesPerUnit) * pxPerUnit;
  scaleBarLine.style.width = Math.max(barPx, 4) + 'px';
  scaleBarLabel.textContent = nice + ' mi';
}
function radiusPxFor(score, zoomLevel) {
  const base = radiusFor(score); // target screen px at full-map zoom (zoomLevel 1)
  const shrunk = base / Math.pow(Math.max(zoomLevel, 1), DOT_SHRINK_EXP);
  return Math.max(shrunk, 2.5);
}
function updateDotSizes() {
  const vb = getViewBox();
  const rect = svg.getBoundingClientRect();
  if (!rect.width || !vb[2]) return;
  const pxPerUnit = rect.width / vb[2];
  const zoomLevel = VB_W / vb[2];
  dotsG.querySelectorAll('.dot').forEach(dot => {
    const score = dot.dataset.score !== '' ? +dot.dataset.score : null;
    dot.setAttribute('r', (radiusPxFor(score, zoomLevel) / pxPerUnit).toFixed(3));
  });
  dotsG.querySelectorAll('.dot-hit').forEach(hit => {
    const score = hit.dataset.score !== '' ? +hit.dataset.score : null;
    const rPx = Math.max(radiusPxFor(score, zoomLevel), 12);
    hit.setAttribute('r', (rPx / pxPerUnit).toFixed(3));
  });
}
document.getElementById('zoomResetBtn').addEventListener('click', resetZoom);
document.getElementById('zoomInBtn').addEventListener('click', () => stepZoom(1 / 1.7));
document.getElementById('zoomOutBtn').addEventListener('click', () => stepZoom(1.7));
document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !isAtFullView()) resetZoom(); });
window.addEventListener('resize', onViewportChange);

// ---- wheel zoom (centered on cursor) ----
svg.addEventListener('wheel', (e) => {
  e.preventDefault();
  const rect = svg.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  const vb = getViewBox();
  const mx = vb[0] + (e.clientX - rect.left) / rect.width * vb[2];
  const my = vb[1] + (e.clientY - rect.top) / rect.height * vb[3];
  const factor = Math.exp(e.deltaY * 0.0015);
  const rawW = vb[2] * factor, rawH = vb[3] * factor;
  const [, , newW, newH] = clampViewBox(vb[0], vb[1], rawW, rawH);
  const newX = mx - (mx - vb[0]) * (newW / vb[2]);
  const newY = my - (my - vb[1]) * (newH / vb[3]);
  const [x, y, w, h] = clampViewBox(newX, newY, newW, newH);
  if (vbAnim) { cancelAnimationFrame(vbAnim); vbAnim = null; }
  setViewBox(x, y, w, h);
  currentZoom = null;
  updateZoomUI();
  onViewportChange();
}, { passive: false });

// ---- click-drag panning (native click still fires for a plain click/tap) ----
let panState = null;
svg.addEventListener('mousedown', (e) => {
  if (e.button !== 0) return;
  panState = { startX: e.clientX, startY: e.clientY, vb0: getViewBox(), moved: false };
});
window.addEventListener('mousemove', (e) => {
  if (!panState) return;
  const dx = e.clientX - panState.startX, dy = e.clientY - panState.startY;
  if (!panState.moved && Math.abs(dx) < 4 && Math.abs(dy) < 4) return;
  panState.moved = true;
  const rect = svg.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  const vb0 = panState.vb0;
  const ux = dx / rect.width * vb0[2], uy = dy / rect.height * vb0[3];
  const [x, y, w, h] = clampViewBox(vb0[0] - ux, vb0[1] - uy, vb0[2], vb0[3]);
  setViewBox(x, y, w, h);
  svg.style.cursor = 'grabbing';
  onViewportChange();
});
window.addEventListener('mouseup', () => {
  if (!panState) return;
  const wasMoved = panState.moved;
  panState = null;
  svg.style.cursor = '';
  if (wasMoved) {
    currentZoom = null;
    updateZoomUI();
    // swallow the click the browser fires right after mouseup for this drag,
    // so it doesn't also trigger a state-zoom or site-pin under the cursor
    document.addEventListener('click', (ev) => { ev.stopPropagation(); ev.preventDefault(); }, { capture: true, once: true });
  }
});

function fmt(v, d) {
  if (v == null || v === '') return '—';
  if (typeof v === 'number') return d != null ? v.toFixed(d) : v.toLocaleString();
  return v;
}

function showHoverTip(e, s) {
  hoverTip.textContent = '#' + (s.rank ?? '?') + ' ' + (s.name || '(unnamed)') + ' (' + fmt(s.score,0) + ')';
  hoverTip.classList.add('show');
  positionHoverTip(e);
}
function positionHoverTip(e) {
  const stage = document.querySelector('.map-stage').getBoundingClientRect();
  hoverTip.style.left = (e.clientX - stage.left + 14) + 'px';
  hoverTip.style.top = (e.clientY - stage.top + 14) + 'px';
}
function hideHoverTip() { hoverTip.classList.remove('show'); }

function pinSite(s) {
  pinned = s;
  infoPanel.innerHTML = '';

  const h2 = document.createElement('h2');
  h2.textContent = s.name || '(unnamed site)';
  infoPanel.appendChild(h2);

  const row1 = document.createElement('div');
  row1.style.margin = '4px 0';
  const conf = s.conf || 'UNVERIFIED';
  const badge = document.createElement('span');
  badge.className = 'confidence conf-' + conf;
  badge.textContent = conf;
  row1.appendChild(badge);
  const statePill = document.createElement('span');
  statePill.className = 'state-pill';
  const pdot = document.createElement('span');
  pdot.className = 'dot';
  pdot.style.background = DATA.states[s.state].dark;
  statePill.appendChild(pdot);
  const pname = document.createElement('span');
  pname.textContent = DATA.states[s.state].name;
  statePill.appendChild(pname);
  row1.appendChild(statePill);
  infoPanel.appendChild(row1);

  const scoreLine = document.createElement('div');
  scoreLine.style.color = '#888';
  scoreLine.style.fontSize = '12px';
  scoreLine.style.marginTop = '4px';
  scoreLine.textContent = 'Score: ' + fmt(s.score, 1);
  infoPanel.appendChild(scoreLine);

  const bar = document.createElement('div');
  bar.className = 'score-bar';
  const fill = document.createElement('div');
  fill.className = 'fill';
  const pct = Math.min((s.score || 0) / 100, 1) * 100;
  fill.style.width = pct + '%';
  fill.style.background = scoreColor(s.score);
  bar.appendChild(fill);
  infoPanel.appendChild(bar);

  function addSection(title, rows) {
    const h3 = document.createElement('h3');
    h3.textContent = title;
    infoPanel.appendChild(h3);
    rows.forEach(([label, val]) => {
      const f = document.createElement('div');
      f.className = 'field';
      const l = document.createElement('span');
      l.className = 'label'; l.textContent = label;
      const v = document.createElement('span');
      v.className = 'value'; v.textContent = val;
      f.appendChild(l); f.appendChild(v);
      infoPanel.appendChild(f);
    });
  }

  addSection('Location', [
    ['City', s.city || '—'],
    ['County', (s.county || '—') + ' Co.'],
    ['Type', s.type || '—'],
    ['Owner', s.owner || '—'],
  ]);
  addSection('Site', [
    ['Parcel acres', fmt(s.acres, 1)],
    ['Rank (in state)', s.rank != null ? ('#' + s.rank) : '—'],
  ]);

  const h3n = document.createElement('h3');
  h3n.textContent = 'Notes';
  infoPanel.appendChild(h3n);
  const notesWrap = document.createElement('div');
  notesWrap.style.marginTop = '4px';
  const textarea = document.createElement('textarea');
  textarea.className = 'notes-box';
  textarea.placeholder = 'Add your own notes about this site (saved in this browser only)…';
  textarea.value = loadNote(s);
  const savedTag = document.createElement('span');
  savedTag.className = 'notes-saved';
  textarea.addEventListener('input', () => {
    saveNote(s, textarea.value);
    savedTag.textContent = 'Saved';
    savedTag.classList.add('show');
    clearTimeout(textarea._saveTimer);
    textarea._saveTimer = setTimeout(() => savedTag.classList.remove('show'), 1200);
  });
  notesWrap.appendChild(textarea);
  notesWrap.appendChild(savedTag);
  infoPanel.appendChild(notesWrap);
}

function siteKey(s) {
  return [s.state, s.name, s.county].join('::');
}
function loadAllNotes() {
  try {
    return JSON.parse(localStorage.getItem('dc_screener_notes') || '{}');
  } catch (e) { return {}; }
}
function loadNote(s) {
  const all = loadAllNotes();
  return all[siteKey(s)] || '';
}
function saveNote(s, text) {
  try {
    const all = loadAllNotes();
    const key = siteKey(s);
    if (text.trim()) all[key] = text; else delete all[key];
    localStorage.setItem('dc_screener_notes', JSON.stringify(all));
  } catch (e) { /* localStorage unavailable — notes won't persist this session */ }
}

function updateStats(n) {
  statsBar.innerHTML = '';
  const strong = document.createElement('strong');
  strong.textContent = n;
  statsBar.appendChild(document.createTextNode('Showing '));
  statsBar.appendChild(strong);
  statsBar.appendChild(document.createTextNode(' / ' + DATA.sites.length + ' sites'));
}

// ---- table view ----
const tableBody = document.getElementById('tableBody');
let sortKey = 'score', sortDir = -1;
function renderTable() {
  const filtered = DATA.sites.filter(matchesFilters);
  filtered.sort((a,b) => {
    let av = a[sortKey], bv = b[sortKey];
    if (av == null) av = sortDir === 1 ? Infinity : -Infinity;
    if (bv == null) bv = sortDir === 1 ? Infinity : -Infinity;
    if (typeof av === 'string') return sortDir * av.localeCompare(bv);
    return sortDir * (av - bv);
  });
  tableBody.innerHTML = '';
  filtered.forEach(s => {
    const tr = document.createElement('tr');
    const tdState = document.createElement('td');
    const tag = document.createElement('span'); tag.className = 'state-tag';
    const dot = document.createElement('span'); dot.className = 'dot';
    dot.style.background = DATA.states[s.state].dark;
    tag.appendChild(dot);
    const stxt = document.createElement('span'); stxt.textContent = s.state;
    tag.appendChild(stxt);
    tdState.appendChild(tag);
    const tdName = document.createElement('td'); tdName.textContent = s.name || '—';
    const tdCounty = document.createElement('td'); tdCounty.textContent = s.county || '—';
    const tdScore = document.createElement('td'); tdScore.className = 'num'; tdScore.textContent = fmt(s.score,1);
    const tdAcres = document.createElement('td'); tdAcres.className = 'num'; tdAcres.textContent = fmt(s.acres,1);
    const tdConf = document.createElement('td'); tdConf.textContent = s.conf || '—';
    const tdType = document.createElement('td'); tdType.textContent = s.type || '—';
    [tdState, tdName, tdCounty, tdScore, tdAcres, tdConf, tdType].forEach(td => tr.appendChild(td));
    tr.style.cursor = 'pointer';
    tr.addEventListener('click', () => { pinSite(s); btnMap.click(); });
    tableBody.appendChild(tr);
  });
  document.getElementById('tableCount').textContent = filtered.length + ' / ' + DATA.sites.length + ' sites';
}
document.querySelectorAll('#dataTable th').forEach(th => {
  th.addEventListener('click', () => {
    const key = th.dataset.key;
    if (sortKey === key) sortDir *= -1; else { sortKey = key; sortDir = -1; }
    renderTable();
  });
});

const btnMap = document.getElementById('btnMap');
const btnTable = document.getElementById('btnTable');
const tablePanel = document.getElementById('tablePanel');
btnMap.addEventListener('click', () => {
  btnMap.classList.add('active'); btnTable.classList.remove('active');
  tablePanel.style.display = 'none';
});
btnTable.addEventListener('click', () => {
  btnTable.classList.add('active'); btnMap.classList.remove('active');
  tablePanel.style.display = 'block';
  renderTable();
});
document.getElementById('btnBackToMap').addEventListener('click', () => btnMap.click());

render();
renderTable();
onViewportChange();
</script>
"""

n_sites = len(payload['sites'])
n_states = len(payload['states'])
html = HTML.replace('__DATA_JSON__', data_json).replace('__SITE_COUNT__', str(n_sites)).replace('__STATE_COUNT__', str(n_states))

out_path = os.path.join(REPO_ROOT, 'index.html')
with open(out_path, 'w') as f:
    f.write(html)
print('wrote', out_path, len(html), 'bytes')
