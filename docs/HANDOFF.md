# HANDOFF — read me first

Written 2026-08-22, end of the session that shipped 0.4.0 and 0.5.0.
Current release: **0.5.0**, merged to `main` and pushed.

## What Gnomon is

A Home Assistant add-on that polls a list of GitHub repositories, reads the YAML
front-matter block at the top of each repo's `STATE.md`, and serves a
single-page board over HA ingress. Read almost entirely on an iPhone, in the HA
Companion App.

**Read-only.** Editing from the panel is deliberately out of scope.

**The governing rule:** facts come from the GitHub API, judgments come from
`STATE.md`. Anything derivable is derived. Nothing that can rot by hand is
stored by hand.

## Where the code is

| File | Lines | Responsibility | Imports |
|---|---|---|---|
| `gnomon/state.py` | 169 | Parse `STATE.md` — front-matter, steps, dates, normalisation, vanished-field diffing | `yaml`, stdlib |
| `gnomon/ranking.py` | 159 | Momentum, debt, ordering, roles, human-readable reasons | stdlib only |
| `gnomon/github.py` | 82 | The three API calls and their error notes | `aiohttp` |
| `gnomon/app.py` | 310 | Options, card assembly, `/data` persistence, HTTP routes | all of the above |
| `gnomon/selftest.py` | 552 | The entire test suite | `state` + `ranking` only |
| `gnomon/www/index.html` | 874 | The whole panel — tokens, layout, render | none |

**`state.py` and `ranking.py` must never import `aiohttp`.** That is what lets
`python3 gnomon/selftest.py` run outside the container. A test in `selftest.py`
enforces it — keep it passing.

## How to test

```bash
python3 gnomon/selftest.py          # 89 assertions, must exit 0
```

`aiohttp` is NOT installed on Anthony's Mac, so `app.py` and `github.py` cannot
be imported or run locally — verify them with
`python3 -c "import ast; ast.parse(open('gnomon/app.py').read())"`.

**The panel has no committed test.** It is verified with hand-written DOM-stub
harnesses under Node, kept in a scratchpad and never committed. If you change
`index.html`, write one: extract the `<script>` block, stub `createElement` /
`createElementNS` / `appendChild` / `className` / `textContent` / `setAttribute`
/ `classList` / `style.setProperty` / `getElementById`, drive `render()`, and
walk the resulting tree.

**A browser cannot be opened** — localhost is blocked by policy in this
environment. Everything visual is verified by static inspection, contrast
arithmetic, and the DOM stub. Anthony is the only one who can look at it.

## How the board works

### Ordering — two tiers

1. **Deadline.** Any card with a `target` within 30 days, or overdue, comes
   first — soonest first.
2. **Momentum.** Everything else, descending:
   `momentum = (commits in 7d x 3) + commits in 30d`

Ties break on `stakes` (revenue, product, personal), then repo name.

Momentum counts commits on the **default branch only** — the commits call sends
no `sha`, so unmerged feature-branch work does not raise it even though
`pushed_at` still counts that push as fresh.

### Debt marks a card and never moves one

```
debt = age / stale_days  +  1.5 if blocked  +  2.0 if overdue
```

Debt is never read by the sort key. There is a test, `selftest_debt_never_orders`,
that exists solely to defend this — it was added because a mutation injecting
debt as a tiebreak passed the entire suite unnoticed.

### Roles

- **hero** — top card, leads with its `[>]` step as the largest text on screen.
  Suppressed only when all three hold: no `[>]`, no target within 30 days, and
  momentum exactly `0`. **Unknown momentum does not suppress it.**
- **rescue** — at most one. Highest debt among cards ranked 5th or lower,
  excluding `parked`, requiring `debt >= 1.0`. A card already in the top four is
  never rescued — it does not need surfacing. Renders nothing when nothing
  qualifies.
- **tail** — everything else, in sort order.

### The rule that keeps being violated

**Unknown is not zero.** `commits_7d` / `commits_30d` / `momentum` are `null`
when the activity call failed. That is different from a genuinely quiet project,
and three separate bugs in this project came from collapsing them. Any new code
touching activity must preserve the distinction.

## The panel

Summary panel (completion ring, week's commit total, stakes split), then hero,
then optional rescue, then tail rows carrying activity bars and pace arrows.

**Pace:** `ratio = commits_7d / (commits_30d / 4.3)`, up at `>= 1.25`, down at
`<= 0.6`, nothing between — and **suppressed entirely below 10 commits in 30
days**, because under that floor a single commit reads as a 4.3x surge.

**Two palettes**, both taken from `~/Code/argus/design/tokens.css`: Halo at
night on bare `:root`, Daylight by day inside
`@media (prefers-color-scheme: light)`. Switched by the device, with no toggle,
no config option and nothing stored — the panel is barred from `localStorage`.

**`prefers-color-scheme` follows iOS, not Home Assistant's theme setting.** If
HA is pinned dark while the phone is in Light, the light panel renders inside a
dark HA shell.

### Panel constraints, all enforced by checks

- **No `innerHTML`**, no HTML-string concatenation, no `esc()` helper. DOM
  construction only. This was a deliberate decision over keeping escaped
  `innerHTML` — with `textContent` a string cannot become markup, which is
  structural rather than a discipline.
- **Every colour is a token.** No `#rrggbb` or `rgba()` outside `:root` or the
  light media query. Verify with no carve-outs — a check that excludes its own
  failure is not a check.
- No `localStorage` / `sessionStorage`, no external fonts, CDNs, scripts or
  images. The SVG namespace is the only permitted URL.
- **Relative fetch paths only** — `fetch("api/projects")`. A leading slash
  breaks HA ingress.
- `var()` does not resolve inside SVG presentation attributes. `stroke="var(…)"`
  renders an invisible ring with no error. Ring strokes are set by CSS class.

## Deploying

Push to `main`, then in HA: Settings → Add-ons → Add-on Store → ⋮ → **Check for
updates**, hard-reload, then **Update**.

**Update, not Restart** — the panel is baked into the container image.

**The frontend caches separately.** A half-updated board (new ordering, old
tiles) means the browser cached `index.html`. Companion app → Settings →
Companion app → Debugging → **Reset frontend cache**, then force-quit.

## What is on the board right now

12 repos configured, 10 reporting. Ten of them were seeded with headers in one
sitting on 2026-08-17, which reset every `pushed_at` — so **freshness and the
rescue slot are both flat until roughly 1 September**, when real ages spread out
again. That is expected, not broken.

`anthonyvenitis.com` is the hero: ships **2026-09-02**, the only targeted
`revenue` project, and decelerating — 2 commits a week against a 25-a-month
average. That deceleration-into-a-deadline is the fact the whole 0.5.0 release
was built to surface.

## Standing rules that bind this repo

- **Never commit, push, or bump a version without explicit permission.** Anthony
  says "commit" / "push" / "yes". Implement, verify, summarise, stop.
- **No attribution of any kind** — no co-author trailers, no generated-by
  notes, nothing describing how the code was produced. Commit messages describe
  the change only. The author is Anthony Venitis.
- **No emoji anywhere** — code, docs, UI, commits. Geometric glyphs only
  (`· ◈ ↑ ↓ ✓ ● ○ —`).
- Never stage `.DS_Store`, `__pycache__`, archives or backups.
- Report what was actually done, including anything repaired beyond the request.

## Next step

See `STATE.md`'s `## Open` section for the live list, and `docs/known-issues.md`
for parked technical findings from both releases.

The momentum-tier `order_reason` fix is **done and unreleased** — the version
has not been bumped, per the standing rule. `ranking.order_reason` now returns
`"momentum 154 - 18 this week, 100 this month"` for the momentum tier instead of
restating the week's count. The collapsed row still shows `18/wk`; the
arithmetic is in the expanded view, which already renders `order_reason`
verbatim. `gnomon/ranking.py` and `gnomon/selftest.py` only — no panel change.
The suite is 89 assertions and exits 0.

The strongest remaining candidate is the `--unknown-c` routing in
`docs/known-issues.md` — it reaches `.seg.done` via `--accent`, so an
unknown-state card's progress reads 0% regardless of real progress. That one is
a panel change, so it needs a DOM stub harness.
