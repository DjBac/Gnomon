# Activity Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Gnomon's four stat tiles with a summary panel, give every project an activity bar and pace arrow, and adopt the Argus design system in a night and a day palette that switch automatically.

**Architecture:** Everything happens in one self-contained file, `gnomon/www/index.html`. The CSS moves to Argus's token names, with the Halo palette on bare `:root` and the Daylight palette overriding it inside `@media (prefers-color-scheme: light)` — so the theme follows the device with no toggle, no config and no storage. All numbers are computed in the browser from card fields the panel already receives; no Python file is touched.

**Tech Stack:** Vanilla HTML/CSS/JS, single file, no build step, no dependencies. Tested with a hand-written DOM stub under Node v22.

**Spec:** `docs/superpowers/specs/2026-08-21-activity-dashboard-design.md`

## Global Constraints

- **No backend change.** Do not modify `gnomon/app.py`, `gnomon/ranking.py`, `gnomon/state.py`, `gnomon/github.py` or `gnomon/selftest.py`.
- **No new dependencies**, no build step, no bundler, no test framework.
- **No `innerHTML`**, no HTML-string concatenation. DOM construction with `createElement` / `createElementNS` / `textContent` only. There is no `esc()` helper and none is to be added.
- **No `localStorage`, no `sessionStorage`**, no external fonts, CDNs, scripts or images. No `http://` or `https://` URLs anywhere except the SVG namespace string.
- **Relative fetch paths only** — `fetch("api/projects")`, never `/api/projects`; a leading slash breaks HA ingress.
- **No attribution of any kind** in code, comments, docs or commit messages.
- **No emoji anywhere** — in code, UI text, docs or commit messages. Geometric glyphs only.
- **Every colour is a token.** Components reference `var(--…)`; no component rule may contain a colour literal. A colour defined only inside the media query is the classic unreadable-theme bug.
- Do not modify `build.yaml`, `run.sh`, `repository.yaml`, `README.md`, `.gitignore`, `Dockerfile`.
- Test harnesses live in `/private/tmp/claude-501/-Users-Anthony-Code-gnomon/4cfc8f97-2c01-4464-b4f3-10ee0c296ef6/scratchpad/` and are never committed.

## Environment facts

- `node` v22 is available. `aiohttp` is NOT installed, so the Python backend cannot run — irrelevant here, nothing Python is touched.
- `python3 gnomon/selftest.py` must still exit 0 after every task (it does not cover the panel, but must not regress).
- A browser cannot be opened: localhost is blocked by policy. All verification is static checks plus the DOM stub.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `gnomon/www/index.html` | The entire panel — tokens, layout, render logic | All four tasks |
| `gnomon/DOCS.md` | User-facing docs | Task 4 |
| `gnomon/CHANGELOG.md` | Release notes | Task 4 |
| `gnomon/config.yaml` | Version string | Task 4 |

The panel stays one file. That is a product requirement — it is served directly to the browser with no build step — not an accident to be refactored away.

---

## Task 1: Adopt the Argus tokens and both palettes

Pure restyle. **No structural or behavioural change.** The gate is that the rendered DOM is byte-identical before and after, while every colour now resolves through a token that has both a night and a day value.

**Files:**
- Modify: `gnomon/www/index.html` — the `:root` block at line 9, and every component rule that names a colour

**Interfaces:**
- Consumes: nothing.
- Produces: the token names every later task uses — `--ok`, `--warn`, `--crit`, `--run`, `--stale-c`, `--text`, `--text-2`, `--text-3`, `--surface`, `--surface-hi`, `--border`, `--track`, `--ground`, `--blur`, `--shadow-card`, plus the `--fs-*`, `--r-*` and `--track-*` scales.

- [ ] **Step 1: Replace the `:root` block**

Replace the whole existing `:root { … }` block (starts line 9) with:

```css
:root {
  /* type scale — argus/design/tokens.css, exact px */
  --fs-micro: 10px;   --fs-label: 11px;  --fs-caption: 11.5px;
  --fs-note: 12px;    --fs-small: 12.5px; --fs-body-dense: 13px;
  --fs-body: 14px;    --fs-emph: 15px;   --fs-title: 16px;
  --fs-panel: 19px;   --fs-num: 20px;    --fs-bignum: 34px;

  --track-caps: .08em;
  --track-tight: -.02em;

  --r-bar: 2px;  --r-xs: 6px;  --r-sm: 8px;  --r-md: 12px;
  --r-lg: 16px;  --r-xl: 20px; --r-2xl: 24px; --r-pill: 999px;

  --ease-lift: cubic-bezier(.2, .8, .2, 1);
  --t-lift: 200ms;
  --lift-y: -2px;

  --font-ui: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI",
             system-ui, sans-serif;
  --mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;

  /* ---------- NIGHT · Halo ---------- */
  --ground: radial-gradient(120% 140% at 20% 0%, #182030 0%, #0e1219 55%, #0a0c10 100%);
  --bg: #0b0d10;
  --surface: rgba(255, 255, 255, .045);
  --surface-hi: rgba(255, 255, 255, .09);
  --border: rgba(255, 255, 255, .08);
  --blur: blur(20px) saturate(160%);
  --shadow-card: none;

  --text: #e8eaee;
  --text-2: #9aa3b2;
  --text-3: #6d7684;
  --track: rgba(255, 255, 255, .08);

  --ok: #34c759;
  --warn: #febc2e;
  --crit: #e5484d;
  --run: #4c8dff;
  --stale-c: #6d7684;
}

/* ---------- DAY · Daylight ---------- */
@media (prefers-color-scheme: light) {
  :root {
    --ground: #f4f5f7;
    --bg: #f4f5f7;
    --surface: #ffffff;
    --surface-hi: #fbfbfd;
    --border: rgba(0, 0, 0, .05);
    --blur: none;
    --shadow-card: 0 1px 2px rgba(15, 20, 30, .05), 0 8px 24px rgba(15, 20, 30, .06);

    --text: #16181d;
    --text-2: #59606c;
    --text-3: #7a8290;
    --track: #e6e9ee;

    --ok: #1f9d55;
    --warn: #8a6116;
    --crit: #b42328;
    --run: #1668e3;
    --stale-c: #c3c9d3;
  }
}
```

- [ ] **Step 2: Repoint every component rule at the new tokens**

Work through the stylesheet and replace the old token names and any colour literals. The old names map as follows:

| Old | New |
|---|---|
| `--card` | `--surface` |
| `--card-hi` | `--surface-hi` |
| `--hair` | `--border` |
| `--dim` | `--text-2` |
| `--dimmer` | `--text-3` |
| `--red` | `--crit` |
| `--sans` | `--font-ui` |
| `--bg-glow` | (gone — the gradient is now `--ground`) |

Change `body` to use the ground and shadow tokens:

```css
body {
  margin: 0;
  background: var(--bg);
  background-image: var(--ground);
  background-attachment: fixed;
  color: var(--text);
  font-family: var(--font-ui);
  font-size: var(--fs-body);
  line-height: 1.45;
  padding: env(safe-area-inset-top) env(safe-area-inset-right)
           env(safe-area-inset-bottom) env(safe-area-inset-left);
  -webkit-font-smoothing: antialiased;
  font-variant-numeric: tabular-nums;
}
```

`font-variant-numeric: tabular-nums` on `body` is what replaces the monospace font for numbers. Then remove the `font-family: var(--mono);` declaration from **all nine rules that carry it** — run `grep -n 'var(--mono)' gnomon/www/index.html` to find them. Each rule keeps its size and letter-spacing and inherits the UI face; `tabular-nums` on `body` is what keeps the digits aligned. Leave the `--mono` token defined in `:root`; Task 4 removes it once nothing references it.

Add the card shadow so Daylight gets its lift:

```css
.card { box-shadow: var(--shadow-card); }
```

Replace the existing `.card` box-shadow line rather than adding a second one.

- [ ] **Step 3: Make the accent map theme-aware**

The `ACCENT` map at line 406 holds raw hex, which cannot follow the theme. Replace it with token references — a custom property value may itself be a `var()`, so this resolves per theme with no JavaScript:

```javascript
  var ACCENT = {
    blocked: "var(--crit)",
    stale:   "var(--stale-c)",
    aging:   "var(--warn)",
    fresh:   "var(--ok)",
    parked:  "var(--run)",
    unknown: "var(--text-3)"
  };
```

`accent(c)` and `cardShell`'s `card.style.setProperty("--accent", accent(c))` are unchanged and keep working.

- [ ] **Step 4: Check no component rule holds a colour literal**

Run:
```bash
cd /Users/Anthony/Code/gnomon
awk '/^:root \{/,/^\}/' gnomon/www/index.html > /tmp/root.txt
awk '/prefers-color-scheme: light/,/^}/' gnomon/www/index.html > /tmp/light.txt
grep -nE '#[0-9a-fA-F]{3,8}|rgba?\(' gnomon/www/index.html \
  | grep -vFf <(grep -oE '#[0-9a-fA-F]{3,8}|rgba?\([^)]*\)' /tmp/root.txt /tmp/light.txt | sed 's/^[^:]*://') \
  || echo "PASS: no colour literals outside the token blocks"
```
Expected: `PASS: no colour literals outside the token blocks`. If any line is listed, replace that literal with the token whose value it duplicates.

- [ ] **Step 5: Prove the DOM did not change**

Build a harness at `/private/tmp/claude-501/-Users-Anthony-Code-gnomon/4cfc8f97-2c01-4464-b4f3-10ee0c296ef6/scratchpad/task1-regression.js` that extracts the script from `gnomon/www/index.html`, runs `render()` against a fixture of one hero, one rescue and three tail cards under a DOM stub implementing `createElement`, `createElementNS`, `appendChild`, `className`, `textContent`, `setAttribute`, `classList`, `style.setProperty` and `getElementById`, then serialises the tree to a string of tag names, classes and text.

Capture that serialisation from `git stash` of the pre-task file and from the post-task file, and diff them.

Expected: identical. Any difference means this task changed behaviour, which it must not.

- [ ] **Step 6: Static constraint check**

Run:
```bash
cd /Users/Anthony/Code/gnomon
grep -q 'innerHTML' gnomon/www/index.html && echo "FAIL innerHTML" || echo "PASS: no innerHTML"
grep -qE "['\"]/api/" gnomon/www/index.html && echo "FAIL leading slash" || echo "PASS: relative fetch"
grep -qiE 'localStorage|sessionStorage|<script src|cdn' gnomon/www/index.html && echo "FAIL external/storage" || echo "PASS: no storage or external refs"
python3 gnomon/selftest.py >/dev/null 2>&1 && echo "PASS: python suite still green"
```
Expected: four PASS lines.

- [ ] **Step 7: Commit**

```bash
git add gnomon/www/index.html
git commit -m "Adopt the Argus tokens with a night and a day palette"
```

---

## Task 2: The summary panel

**Files:**
- Modify: `gnomon/www/index.html` — the `.tiles` markup at lines 392-397, the `.tile` CSS at line 86, and `tally()` at line 585

**Interfaces:**
- Consumes: `el(tag, className, text)`, `addIf(parent, child)` and the tokens from Task 1.
- Produces:
  - `svgEl(tag, attrs) -> SVGElement`
  - `completionRing(done, total) -> SVGElement | null`
  - `summaryLine(cards) -> string`
  - `stakesBar(cards) -> HTMLElement | null`
  - `renderSummary(cards) -> void` — replaces `tally`, called from the same place with the same argument

- [ ] **Step 1: Write the failing tests**

Create `/private/tmp/claude-501/-Users-Anthony-Code-gnomon/4cfc8f97-2c01-4464-b4f3-10ee0c296ef6/scratchpad/task2-summary.js`. It must extract the real script from `gnomon/www/index.html`, run it under a DOM stub, and reach the functions via a probe. Assert:

```javascript
// ring geometry — the documented formula
//   dashoffset = 251.3 * (1 - done/total)
assert(offsetOf(completionRing(51, 79)) === 89.07);   // 251.3 * (1 - 51/79) = 89.0683… → 89.07
assert(offsetOf(completionRing(0, 10)) === 251.3);    // nothing done → full offset
assert(offsetOf(completionRing(10, 10)) === 0);       // all done → no offset
assert(completionRing(0, 0) === null);                // no steps anywhere → no ring

// summary line — conditional segments
assert(summaryLine(cards({done:51,total:79})) === "51 of 79 steps · 65%");
assert(summaryLine(cards({done:51,total:79,idle:5})) === "51 of 79 steps · 65% · 5 idle");
assert(summaryLine(cards({done:51,total:79,idle:5,blocked:2,stale:1}))
       === "51 of 79 steps · 65% · 5 idle · 2 blocked · 1 stale");
assert(summaryLine(cards({done:0,total:0})) === "");   // no steps → no completion segment

// idle rule — a [>] with <=2 commits counts; done-and-quiet does not; unknown does not
assert(idleCount([{next:"x", commits_7d:2}]) === 1);
assert(idleCount([{next:"",  commits_7d:0}]) === 0);
assert(idleCount([{next:"x", commits_7d:null}]) === 0);

// stakes bar
assert(stakesBar(zeroCommitCards) === null);           // shares of zero are undefined
assert(widthsOf(stakesBar(realCards)) === ["13%","34%","53%"]);
assert(stakesBar([{stakes:"revenue", commits_7d:null}]) === null); // unknown excluded
```

These reference helpers you must define in the harness. The harness scaffold —
reused by Task 3, so write it once and require it from there:

```javascript
// ---- DOM stub: only what the panel actually uses ----
function node(tag, ns) {
  return {
    tagName: tag.toUpperCase(), ns: ns || null, className: "", textContent: "",
    children: [], attrs: {}, style: { setProperty: function (k, v) { this[k] = v; } },
    classList: { add: function () {}, toggle: function () {}, contains: function () { return false; } },
    appendChild: function (c) { this.children.push(c); return c; },
    insertBefore: function (c) { this.children.unshift(c); return c; },
    setAttribute: function (k, v) { this.attrs[k] = String(v); },
    getAttribute: function (k) { return this.attrs[k]; },
    addEventListener: function () {}, closest: function () { return null; },
    querySelector: function () { return null; }, firstChild: null
  };
}
const els = {};
global.document = {
  createElement: function (t) { return node(t); },
  createElementNS: function (ns, t) { return node(t, ns); },
  getElementById: function (id) { return (els[id] = els[id] || node("div")); },
  addEventListener: function () {}, hidden: false, body: node("body")
};
global.window = global;
global.setInterval = function () { return 0; };
global.fetch = function () { return new Promise(function () {}); };

// ---- load the real script out of the real file ----
const fs = require("node:fs");
const html = fs.readFileSync("/Users/Anthony/Code/gnomon/gnomon/www/index.html", "utf8");
if (html.includes("innerHTML")) throw new Error("innerHTML present — harness refuses to run");
const src = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const probed = src.replace(/  load\(false\);\n\}\)\(\);/,
  "  globalThis.P = { completionRing, summaryLine, idleCount, stakesBar, weekTotal, renderSummary };\n})();");
eval(probed);
const P = globalThis.P;

// ---- assertion helpers the tests above use ----
function offsetOf(svg) { return Number(svg.children[1].attrs["stroke-dashoffset"]); }
function widthsOf(wrap) { return wrap.children[0].children.map(function (i) { return i.style.width; }); }
function card(o) {
  return Object.assign({ project: "p", repo: "o/p", stakes: "personal", state: "fresh",
    next: "", steps_done: 0, steps_total: 0, commits_7d: 0, commits_30d: 0, role: "tail" }, o);
}
let fails = 0;
function check(label, got, want) {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) fails++;
  console.log((ok ? "PASS  " : "FAIL  ") + label + "  " + JSON.stringify(got) +
              (ok ? "" : "  (want " + JSON.stringify(want) + ")"));
}
```

End the file with `process.exit(fails ? 1 : 0)` so a failure is visible to the
shell. Express every assertion above through `check(label, got, want)` rather
than a bare `assert`, so one failure does not hide the rest.

- [ ] **Step 2: Run to verify they fail**

Run: `node /private/tmp/claude-501/-Users-Anthony-Code-gnomon/4cfc8f97-2c01-4464-b4f3-10ee0c296ef6/scratchpad/task2-summary.js`
Expected: FAIL — `completionRing is not defined`.

- [ ] **Step 3: Replace the tiles markup**

Replace lines 392-397 entirely:

```html
  <div id="summary"></div>
```

- [ ] **Step 4: Replace the tile CSS**

Replace the whole `/* ---------- stat tiles ---------- */` block with:

```css
/* ---------- summary ---------- */

#summary { margin: 1rem 0 1.1rem; }

.summary {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r-xl);
  padding: .85rem .9rem .8rem;
  box-shadow: var(--shadow-card);
  -webkit-backdrop-filter: var(--blur);
  backdrop-filter: var(--blur);
}

.sumrow { display: flex; gap: .9rem; align-items: center; }
.sumtext { min-width: 0; }

.sumtext .hdr {
  font-size: var(--fs-micro);
  text-transform: uppercase;
  letter-spacing: var(--track-caps);
  color: var(--text-3);
}
.sumtext .big {
  font-size: var(--fs-num);
  font-weight: 640;
  letter-spacing: var(--track-tight);
  margin-top: .15rem;
}
.sumtext .sub {
  font-size: var(--fs-caption);
  color: var(--text-2);
  margin-top: .1rem;
}

.ring { flex: none; }
.ring-track { stroke: var(--track); }
.ring-fill { stroke: var(--ok); }

.stakes { display: flex; height: 5px; border-radius: var(--r-bar); overflow: hidden; margin: .75rem 0 .4rem; }
.stakes i { display: block; }
.stakekey {
  display: flex; gap: .7rem;
  font-size: var(--fs-micro);
  text-transform: uppercase;
  letter-spacing: var(--track-caps);
  color: var(--text-3);
}
```

The ring strokes are set by class, not by attribute — `var()` does not resolve inside SVG presentation attributes, only in CSS properties. Setting `stroke="var(--track)"` renders nothing.

- [ ] **Step 5: Implement the summary builders**

Insert after `addIf` (line 512):

```javascript
  var SVG_NS = "http://www.w3.org/2000/svg";
  var RING_C = 251.3;
  var STAKES_ORDER = ["revenue", "product", "personal"];

  function svgEl(tag, attrs) {
    var node = document.createElementNS(SVG_NS, tag);
    Object.keys(attrs).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    return node;
  }

  // Argus ring geometry: viewBox 92, r=40, stroke=8, circumference 251.3,
  // rotated -90 so it starts at twelve o'clock.
  function completionRing(done, total) {
    if (!total) return null;
    var pct = Math.round(100 * done / total);
    var offset = Math.round(RING_C * (1 - done / total) * 100) / 100;
    var svg = svgEl("svg", {
      "class": "ring", width: "76", height: "76", viewBox: "0 0 92 92",
      "aria-label": pct + " percent complete"
    });
    svg.appendChild(svgEl("circle", {
      "class": "ring-track", cx: "46", cy: "46", r: "40",
      fill: "none", "stroke-width": "8"
    }));
    svg.appendChild(svgEl("circle", {
      "class": "ring-fill", cx: "46", cy: "46", r: "40",
      fill: "none", "stroke-width": "8", "stroke-linecap": "round",
      "stroke-dasharray": String(RING_C),
      "stroke-dashoffset": String(offset),
      transform: "rotate(-90 46 46)"
    }));
    return svg;
  }

  function idleCount(cards) {
    return cards.filter(function (c) {
      return c.next && typeof c.commits_7d === "number" && c.commits_7d <= 2;
    }).length;
  }

  function summaryLine(cards) {
    var done = 0, total = 0, blocked = 0, stale = 0;
    cards.forEach(function (c) {
      done += c.steps_done || 0;
      total += c.steps_total || 0;
      if (c.state === "blocked") blocked++;
      if (c.state === "stale") stale++;
    });
    var idle = idleCount(cards);
    var parts = [];
    if (total) parts.push(done + " of " + total + " steps · " + Math.round(100 * done / total) + "%");
    if (idle) parts.push(idle + " idle");
    if (blocked) parts.push(blocked + " blocked");
    if (stale) parts.push(stale + " stale");
    return parts.join(" · ");
  }

  function weekTotal(cards) {
    return cards.reduce(function (n, c) {
      return n + (typeof c.commits_7d === "number" ? c.commits_7d : 0);
    }, 0);
  }

  function stakesBar(cards) {
    var by = { revenue: 0, product: 0, personal: 0 };
    var total = 0;
    cards.forEach(function (c) {
      if (typeof c.commits_7d !== "number") return;
      var key = by.hasOwnProperty(c.stakes) ? c.stakes : "personal";
      by[key] += c.commits_7d;
      total += c.commits_7d;
    });
    if (!total) return null;
    var wrap = el("div");
    var bar = el("div", "stakes");
    var key = el("div", "stakekey");
    var tone = { revenue: "var(--ok)", product: "var(--run)", personal: "var(--stale-c)" };
    STAKES_ORDER.forEach(function (k) {
      var pct = Math.round(100 * by[k] / total);
      var seg = el("i");
      seg.style.setProperty("width", pct + "%");
      seg.style.setProperty("background", tone[k]);
      bar.appendChild(seg);
      key.appendChild(el("span", null, pct + "% " + k));
    });
    wrap.appendChild(bar);
    wrap.appendChild(key);
    return wrap;
  }
```

- [ ] **Step 6: Replace `tally` with `renderSummary`**

Delete `tally` entirely (line 585) and put this in its place:

```javascript
  function renderSummary(cards) {
    var host = document.getElementById("summary");
    host.textContent = "";
    if (!cards.length) return;

    var done = 0, total = 0;
    cards.forEach(function (c) { done += c.steps_done || 0; total += c.steps_total || 0; });

    var panel = el("div", "summary");
    var row = el("div", "sumrow");
    addIf(row, completionRing(done, total));

    var text = el("div", "sumtext");
    text.appendChild(el("div", "hdr", "this week"));
    var known = cards.some(function (c) { return typeof c.commits_7d === "number"; });
    text.appendChild(el("div", "big", known ? weekTotal(cards) + " commits" : "activity unknown"));
    var line = summaryLine(cards);
    if (line) text.appendChild(el("div", "sub", line));
    row.appendChild(text);
    panel.appendChild(row);

    addIf(panel, stakesBar(cards));
    host.appendChild(panel);
  }
```

Then change the one call site inside `load()` from `tally(cards)` to `renderSummary(cards)`.

- [ ] **Step 7: Run to verify the tests pass**

Run: `node /private/tmp/claude-501/-Users-Anthony-Code-gnomon/4cfc8f97-2c01-4464-b4f3-10ee0c296ef6/scratchpad/task2-summary.js`
Expected: every assertion PASS.

- [ ] **Step 8: Verify constraints and the python suite**

Run:
```bash
cd /Users/Anthony/Code/gnomon
grep -q 'innerHTML' gnomon/www/index.html && echo "FAIL innerHTML" || echo "PASS: no innerHTML"
grep -q 'id="t-active"' gnomon/www/index.html && echo "FAIL: old tile ids remain" || echo "PASS: tiles removed"
grep -q 'function tally' gnomon/www/index.html && echo "FAIL: tally remains" || echo "PASS: tally removed"
python3 gnomon/selftest.py >/dev/null 2>&1 && echo "PASS: python suite still green"
```
Expected: four PASS lines.

- [ ] **Step 9: Commit**

```bash
git add gnomon/www/index.html
git commit -m "Replace the stat tiles with a summary panel"
```

---

## Task 3: Activity bars and pace arrows

**Files:**
- Modify: `gnomon/www/index.html` — `heroCard` (line 516), `tailRow` (line 552), `render` (line 568)

**Interfaces:**
- Consumes: `el`, `addIf`, `cardShell`, `activityLabel`, `segments`, `blockerBlock`, `detailBlock` from the existing file; tokens from Task 1.
- Produces:
  - `pace(c) -> "up" | "down" | ""`
  - `paceGlyph(c) -> HTMLElement | null`
  - `maxCommits(cards) -> number`
  - `activityBar(c, max) -> HTMLElement | null`
  - `tailRow(c, max)` — signature gains a second parameter

- [ ] **Step 1: Write the failing tests**

Create `/private/tmp/claude-501/-Users-Anthony-Code-gnomon/4cfc8f97-2c01-4464-b4f3-10ee0c296ef6/scratchpad/task3-pace.js` with real assertions:

```javascript
// pace bands
assert(pace({commits_7d: 13, commits_30d: 43}) === "up");    // ratio 1.30
assert(pace({commits_7d: 5,  commits_30d: 43}) === "down");  // ratio 0.50
assert(pace({commits_7d: 10, commits_30d: 43}) === "");      // ratio 1.00

// boundaries are exact
assert(pace({commits_7d: 12.5, commits_30d: 43}) === "up");    // ratio exactly 1.25
assert(pace({commits_7d: 6,    commits_30d: 43}) === "down");  // ratio exactly 0.60

// volume floor — nine is too few to say anything
assert(pace({commits_7d: 9, commits_30d: 9}) === "");
assert(pace({commits_7d: 10, commits_30d: 10}) === "up");

// unknown is not zero
assert(pace({commits_7d: null, commits_30d: 40}) === "");
assert(pace({commits_7d: 5, commits_30d: null}) === "");

// bar scaling counts every card, including hero and rescue
assert(maxCommits([{role:"hero",commits_7d:58},{role:"tail",commits_7d:20}]) === 58);
assert(maxCommits([{commits_7d:null},{commits_7d:3}]) === 3);
assert(maxCommits([{commits_7d:null}]) === 0);

// bars
assert(widthOf(activityBar({commits_7d:29}, 58)) === "50%");
assert(activityBar({commits_7d:null}, 58) === null);   // unknown draws nothing
assert(activityBar({commits_7d:0}, 58) === null);      // zero draws nothing
assert(activityBar({commits_7d:5}, 0) === null);       // no max, nothing to scale against
```

Then structural assertions rendering the real functions under the DOM stub:

- a tail card with `commits_7d: 29`, `commits_30d: 52` renders a `.pace.up` element and an `.actbar` whose inner width is `50%` against a max of 58
- a tail card with `commits_7d: null` renders `—` in its activity slot and no `.actbar`
- the hero's meta row ends with a `.pace` element when its pace is non-empty, and does not when it is empty
- markup injected into `project` still lands only as `textContent`

- [ ] **Step 2: Run to verify they fail**

Run: `node /private/tmp/claude-501/-Users-Anthony-Code-gnomon/4cfc8f97-2c01-4464-b4f3-10ee0c296ef6/scratchpad/task3-pace.js`
Expected: FAIL — `pace is not defined`.

- [ ] **Step 3: Add the CSS**

Append to the `/* ---------- card ---------- */` section:

```css
.pace { font-size: var(--fs-caption); line-height: 1; flex: none; }
.pace.up { color: var(--ok); }
.pace.down { color: var(--crit); }

.actbar {
  height: 4px;
  border-radius: var(--r-bar);
  background: var(--track);
  overflow: hidden;
  flex: 1;
  min-width: 0;
}
.actbar i { display: block; height: 100%; border-radius: var(--r-bar); background: var(--accent); }

.card.tail .row1 { gap: .5rem; }
.card.tail .actbar { margin: 0 .1rem; }
```

- [ ] **Step 4: Implement the helpers**

Insert after `activityLabel` (line 431):

```javascript
  var PACE_WINDOW = 4.3;      // weeks in the 30-day window
  var PACE_FLOOR = 10;        // below this many monthly commits, say nothing
  var PACE_UP = 1.25;
  var PACE_DOWN = 0.6;

  // Direction of travel without storing history: this week against the
  // month's weekly average. Silent below the floor, where the ratio is noise.
  function pace(c) {
    if (typeof c.commits_7d !== "number") return "";
    if (typeof c.commits_30d !== "number" || c.commits_30d < PACE_FLOOR) return "";
    var ratio = c.commits_7d / (c.commits_30d / PACE_WINDOW);
    if (ratio >= PACE_UP) return "up";
    if (ratio <= PACE_DOWN) return "down";
    return "";
  }

  function paceGlyph(c) {
    var dir = pace(c);
    if (!dir) return null;
    return el("span", "pace " + dir, dir === "up" ? "↑" : "↓");
  }

  function maxCommits(cards) {
    return cards.reduce(function (m, c) {
      return typeof c.commits_7d === "number" && c.commits_7d > m ? c.commits_7d : m;
    }, 0);
  }

  function activityBar(c, max) {
    if (!max || typeof c.commits_7d !== "number" || c.commits_7d <= 0) return null;
    var bar = el("div", "actbar");
    var fill = el("i");
    fill.style.setProperty("width", Math.round(100 * c.commits_7d / max) + "%");
    bar.appendChild(fill);
    return bar;
  }
```

- [ ] **Step 5: Give the hero its pace arrow**

In `heroCard`, replace the meta row line:

```javascript
    var meta = metaRow([c.stakes, c.phase, activityLabel(c)]);
    addIf(meta, paceGlyph(c));
    card.appendChild(meta);
```

- [ ] **Step 6: Rebuild the tail row**

Replace `tailRow` entirely:

```javascript
  function tailRow(c, max) {
    var card = cardShell(c, "card tail");
    var row = el("div", "row1");
    row.appendChild(el("span", "project", c.project));
    row.appendChild(el("span", "age", activityLabel(c)));
    addIf(row, paceGlyph(c));
    addIf(row, activityBar(c, max));
    row.appendChild(
      el("span", "count", c.steps_total ? c.steps_done + "/" + c.steps_total : "—")
    );
    card.appendChild(row);
    addIf(card, segments(c));
    addIf(card, blockerBlock(c));
    addIf(card, c.note ? el("div", "note", c.note) : null);
    addIf(card, detailBlock(c));
    return card;
  }
```

- [ ] **Step 7: Pass the maximum through `render`**

In `render`, compute the maximum once across every card — hero and rescue included, so bars do not rescale when the hero changes — and pass it to each tail row:

```javascript
    var max = maxCommits(cards);
    hero.forEach(function (c) { board.appendChild(heroCard(c)); });
    rescue.forEach(function (c) { board.appendChild(rescueCard(c)); });
    tail.forEach(function (c) { board.appendChild(tailRow(c, max)); });
```

- [ ] **Step 8: Run to verify the tests pass**

Run: `node /private/tmp/claude-501/-Users-Anthony-Code-gnomon/4cfc8f97-2c01-4464-b4f3-10ee0c296ef6/scratchpad/task3-pace.js`
Expected: every assertion PASS.

- [ ] **Step 9: Verify constraints**

Run:
```bash
cd /Users/Anthony/Code/gnomon
grep -q 'innerHTML' gnomon/www/index.html && echo "FAIL innerHTML" || echo "PASS: no innerHTML"
grep -c 'paceGlyph' gnomon/www/index.html
python3 gnomon/selftest.py >/dev/null 2>&1 && echo "PASS: python suite still green"
```
Expected: `PASS: no innerHTML`, a count of 4 (one definition plus three call sites), and the python PASS line.

- [ ] **Step 10: Commit**

```bash
git add gnomon/www/index.html
git commit -m "Give every project an activity bar and a pace arrow"
```

---

## Task 4: Release 0.5.0

**Files:**
- Modify: `gnomon/config.yaml`, `gnomon/CHANGELOG.md`, `gnomon/DOCS.md`, `gnomon/www/index.html`

**Interfaces:**
- Consumes: everything from Tasks 1-3.
- Produces: nothing.

- [ ] **Step 1: Bump the version**

`gnomon/config.yaml`, line 3: `version: "0.5.0"`

- [ ] **Step 2: Remove the now-unused mono token**

Run `grep -n 'var(--mono)' gnomon/www/index.html`. If there are no matches, delete the `--mono:` line from `:root`. If there are matches, leave the token and note which rules still use it in your report.

- [ ] **Step 3: Add the changelog entry**

Insert directly after `# Changelog`:

```markdown
## 0.5.0

The top of the board becomes a dashboard, and the panel gains a day theme.

- The four stat tiles are replaced by a summary panel: a completion ring, the
  week's commit total, and a stakes split showing where the effort went
- Every project row now carries an activity bar and a pace arrow, so the shape
  of the week is visible without opening anything
- Pace compares this week against the month's weekly average, and stays silent
  below ten commits in thirty days where the ratio would be noise
- The hero's meta row gains the same arrow, so a decelerating deadline reads at
  a glance
- Adopted the Argus design tokens: its type scale, radii, status hues and ring
  geometry, with tabular numerals replacing the monospace font
- Two palettes — Halo at night, Daylight by day — switched automatically by the
  device's light or dark setting. No toggle and nothing stored
- No backend change, no new API calls, and no STATE.md needs editing
```

- [ ] **Step 4: Document the dashboard in DOCS.md**

Add a `## The dashboard` section after the ordering section, covering:

- what the ring shows (steps done across every tracked project)
- what the stakes split shows and that it is share of the week's commits
- the pace formula `commits_7d / (commits_30d / 4.3)`, the `↑` at 1.25 and `↓` at 0.6, and the ten-commit floor with the reason: below it a single commit reads as a 4.3x surge
- that momentum and pace count commits on the **default branch**, so work on unmerged branches does not raise them
- that the panel follows the device's light or dark setting, with no toggle

- [ ] **Step 5: Update this repo's STATE.md**

Mark `[>] Momentum board with hero and rescue` as `[x]`, and add `[>] Activity dashboard with day and night themes`. Every step string stays double-quoted; exactly one `[>]` remains.

- [ ] **Step 6: Verify**

```bash
cd /Users/Anthony/Code/gnomon
python3 -c "import yaml; [yaml.safe_load(open(f)) for f in ['repository.yaml','gnomon/config.yaml','gnomon/build.yaml']]" && echo "YAML ok"
python3 -c "import sys,yaml; t=open('STATE.md').read(); assert t.startswith('---'); d=yaml.safe_load(t.split('---',2)[1]); s=d.get('steps',[]); assert all(isinstance(x,str) for x in s); cur=[x for x in s if x.startswith('[>]')]; assert len(cur)==1, cur; print(d['project'], len(s),'steps',sum(1 for x in s if x.startswith('[x]')),'done')"
grep -n 'version:' gnomon/config.yaml
python3 gnomon/selftest.py >/dev/null 2>&1 && echo "PASS: python suite green"
node /private/tmp/claude-501/-Users-Anthony-Code-gnomon/4cfc8f97-2c01-4464-b4f3-10ee0c296ef6/scratchpad/task2-summary.js && node /private/tmp/claude-501/-Users-Anthony-Code-gnomon/4cfc8f97-2c01-4464-b4f3-10ee0c296ef6/scratchpad/task3-pace.js
```
Expected: `YAML ok`, the STATE.md line with exactly one current step, `version: "0.5.0"`, the python PASS, and both panel harnesses green.

- [ ] **Step 7: Commit**

```bash
git add gnomon/config.yaml gnomon/CHANGELOG.md gnomon/DOCS.md gnomon/www/index.html STATE.md
git commit -m "Gnomon 0.5.0"
```

- [ ] **Step 8: Stop before pushing**

Do not push. Report what changed and wait for explicit permission.

---

## Self-review notes

**Spec coverage.** Summary panel with ring, totals and stakes → Task 2. Ring geometry and its hidden-when-no-steps rule → Task 2 steps 1 and 5. Conditional idle/blocked/stale segments → Task 2. Idle excluding unknown activity → Task 2 step 1. Hero unchanged but gaining a pace arrow → Task 3 step 5. Rescue card preserved → untouched by every task; Task 1 step 5 asserts the rendered DOM is unchanged, which covers it. Tail rows with bar and arrow → Task 3 step 6. Bar scaling across all cards including hero and rescue → Task 3 steps 1 and 7. Pace formula, bands and volume floor → Task 3. Argus tokens, type scale, radii, tabular numerals → Task 1. Halo night and Daylight day via `prefers-color-scheme` → Task 1 step 1. No colour literal outside the token blocks → Task 1 step 4. Version, changelog, docs → Task 4.

**Known gap, deliberate.** The spec's "all activity unknown" edge case has no dedicated structural test; it is the composition of `weekTotal` returning zero and `stakesBar` returning null, both directly tested, plus the `activity unknown` string which Task 2 step 6 renders from a one-line condition.

**Type consistency.** `pace` returns `"up" | "down" | ""` at its definition and at all three call sites. `maxCommits` returns a number and is the second argument to both `activityBar` and `tailRow`. `completionRing`, `stakesBar` and `activityBar` all return `null` rather than an empty node when they have nothing to draw, matching the `addIf` idiom already in the file. `renderSummary` replaces `tally` with the same single-argument signature.
