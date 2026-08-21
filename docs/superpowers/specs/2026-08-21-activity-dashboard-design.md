# Activity dashboard — design

**Status:** approved 2026-08-21 · target release 0.5.0 · supersedes revision 1

## The problem

The panel's top surface is four stat tiles: Active, Blocked, Stale, Tracked. Two
read zero, a third duplicates what each card's activity label already says, and
the fourth is a constant. The strip costs 70px and answers nothing actionable.

Below it the board answers "what should I do now" well. Nothing answers "where
did my time actually go, and is it going where it matters".

## What measurement decided

Every candidate visual was rendered against the real eleven-repo portfolio before
being chosen.

**Pie charts are out.** The categorical fields are degenerate — the same finding
that killed the old ordering model:

| Pie of… | Reality |
|---|---|
| `state` | one solid circle — 11/11 fresh |
| `has target` | 91% one slice |
| `phase` | 64% one slice |
| `stakes` | 6 / 3 / 2 — the only one with shape |

**Continuous fields have real spread**, which is what bars are for:

```
commits/7d   58  29  23  20  18   2   2   1   1   1   1
progress %  100  86  82  71  71  67  57  57  44  43  33
```

**Concentration ratios are out.** Top-3 share is 71%. True, tidy, and no decision
follows from it.

**Anything trend-based is out.** No persistence exists, and pace (below) gives a
directional read without it.

### The finding that shaped the design

`anthonyvenitis.com` ships in 12 days, is the only `revenue` project with a
target, and its pace has collapsed to a third of its monthly average — 25 commits
over 30 days, 2 in the last 7. Nothing on the board says this. Surfacing that
class of fact is the point of the feature.

## Goal

Replace the four stat tiles with a compact summary, give every project an
activity bar and a pace arrow, and adopt the Argus design system — in a night
theme and a day theme that switch automatically.

### Non-goals

- **No backend change.** No new fields, no new API calls, no persistence. Every
  number is computed in the browser from data the panel already receives.
- **No pie charts.** See above.
- **No filtering, no hiding.** Every tracked project appears on screen.
- **Do not displace the hero.** It must still open above the fold on a 375×812
  iPhone.

## What revision 1 got wrong

Revision 1 specified a summary that ranked five projects by activity, followed by
a tail that listed all eleven by board order — two lists of the same projects.
Everything awkward in it followed from that duplication:

- a top-five cut, to stop the summary being a second full list
- a "N more · N commits" group row, to account for what the cut hid
- a rule pinning the hero into the chart, because the cut would otherwise hide
  the single most valuable pace signal in the portfolio
- an entire interaction design for tapping a chart bar to scroll to its card

**Merging the two lists deletes all four rules.** The summary keeps only what is
genuinely aggregate; every project appears exactly once, in the tail, where its
row now carries the activity bar and pace arrow. Summary height drops from about
240px to about 100px, and all eleven projects are visible instead of five.

## Layout

```
Gnomon                                    00:46   Refresh

┌────────────────────────────────────────────────┐
│   ◜◝    THIS WEEK                              │
│  ◟65%◞  156 commits                            │
│         51 of 79 steps · 65% · 5 idle          │
│                                                 │
│  ▎████████ ██████████████                      │
│  13% revenue  34% product  53% personal        │
└────────────────────────────────────────────────┘

┌────────────────────────────────────────────────┐
│ anthonyvenitis.com                  SHIPS 12d  │
│ ▇▇▇▇▇▇▇▇▇▇▇▇▇▇░░░░░  5/7                       │
│ Drafting quality for venues nobody has visited │
│ revenue · usable · 2/wk ↓                      │
└────────────────────────────────────────────────┘

  Argus                 58 ↑  ████████████  9/11
  Nostos                18     ████          3/7
  Nima                  29 ↑  ██████         4/9
  The Bridge            23 ↑  █████          4/7
  Gnomon                20 ↑  ████           6/7
  Oikovis Automations    2     ▏             4/6
  Pounta Sun-bed         1     ▏             5/5
  Oikovis Pulse          1     ▏             2/6
  Doukas Bus             1     ▏             5/7
  Pilates Auto-Booker    1     ▏             4/7
```

### Summary panel

Replaces the four stat tiles. Three elements:

- **Completion ring** — Argus's documented geometry: viewBox `92 92`, `r=40`,
  `stroke=8`, circumference `251.3`, rotated `-90°`, so
  `stroke-dashoffset = 251.3 × (1 − done/total)`. Rendered at 76px on mobile.
  Hidden when no project has any steps, since a ring of nothing is decoration.
- **Week totals** — `THIS WEEK`, the commit total, then a line reading
  `<done> of <total> steps · <pct>%`, with `<n> idle`, `<n> blocked` and
  `<n> stale` appended only when non-zero.
- **Stakes split** — one segmented bar, revenue / product / personal share of the
  week's commits, with percentage labels. Hidden when the week's total is zero.
  This is the only place `stakes` does real work now that ordering demoted it to
  a tiebreak.

### Hero card

Unchanged from 0.4.0 in structure and dominance — the `[>]` step remains the
largest text on screen. Only the palette and type scale change. Its meta row
gains the pace arrow, so a decelerating deadline reads in one glance.

The hero does **not** repeat as a tail row.

### Rescue card

**Unchanged from 0.4.0.** When a project clears the debt floor it renders between
the hero and the tail, in its existing form. It is not currently visible — no
repo is blocked or stale — but it is part of the layout and takes the new
palette like everything else. A rescued project does **not** also appear in the
tail.

### Tail rows

Every project except the hero and the rescue, in board order, one row each: name, `commits_7d`, pace arrow,
activity bar, steps fraction. Bar width is linear against the highest `commits_7d` among **all** cards with
known activity, including the hero and any rescue. Scaling only to the tail would
make the bars rescale whenever the hero changed, which would read as movement
where none happened.

Tapping a row expands it into the full step list and reasoning line, exactly as
today. **No new interaction is introduced** — the chart-to-card navigation from
revision 1 is unnecessary once the chart and the list are the same thing.

### Pace arrows

```
ratio = commits_7d / (commits_30d / 4.3)
```

- `↑` when `ratio >= 1.25`
- `↓` when `ratio <= 0.6`
- nothing in between

**Suppressed entirely when `commits_30d < 10`.** Below that there is not enough
history to say anything, and a fabricated arrow is worse than none.

The floor does real work. Argus reads x4.3 because 58 of its 58 monthly commits
landed this week — genuine acceleration, honest arrow. Pilates Auto-Booker reads
x4.3 off a single commit, which is noise. Same ratio, opposite meanings,
separated by volume alone.

## Themes

Two palettes, both taken verbatim from `argus/design/tokens.css`.

**Night — Halo.** Radial-gradient ground `#182030 → #0e1219 → #0a0c10`, glass
panels at `rgba(255,255,255,.045)` on `rgba(255,255,255,.08)` borders with
`blur(20px) saturate(160%)`. Status hues `#34c759` / `#febc2e` / `#e5484d` /
`#4c8dff` / `#6d7684`.

**Day — Daylight.** Ground `#f4f5f7`, surfaces `#ffffff`, text `#16181d` /
`#59606c` / `#7a8290`, borders `rgba(0,0,0,.05)`, card shadow
`0 1px 2px rgba(15,20,30,.05), 0 8px 24px rgba(15,20,30,.06)`. Accent `#1668e3`,
green `#1f9d55`, and the tinted status pills (`--pill-ok-bg` / `--pill-ok-text`
and siblings).

**Switching is automatic via `prefers-color-scheme`**, with night as the bare
`:root` default and day applied under `@media (prefers-color-scheme: light)`.
This follows the phone, which is what makes it night/day without anything being
stored. No toggle, no config option, no `localStorage` — the storage ban is why
a manual override was rejected. If one is ever wanted it needs an add-on config
option, and that is a separate decision.

Every colour is defined as a token on `:root` and overridden only inside the
media query. No component may reference a literal that works in one theme only.

### Adopted from the Argus token file

| | Value |
|---|---|
| Type scale | named px steps, 10 / 11 / 11.5 / 12 / 12.5 / 13 / 14 / 15 / 16 / 19 / 20 / 34 |
| Numerals | `font-variant-numeric: tabular-nums` on the UI face, replacing the monospace font |
| Radii | `2px` bar · `6px` chip · `12px` button · `16px` frame · `20px` card · `999px` pill |
| Motion | `--ease-lift: cubic-bezier(.2,.8,.2,1)`, `--t-lift: 200ms`, `--lift-y: -2px` |
| Ring | `92` viewBox, `r=40`, `stroke=8`, `c=251.3` |

Gnomon's current shell background `#0B0D10` and card fill
`rgba(255,255,255,.045)` are already identical to Argus's, so the ground does not
move.

## Data

Derived in the browser from fields already on each card: `project`, `repo`,
`role`, `stakes`, `state`, `next`, `steps_done`, `steps_total`, `commits_7d`,
`commits_30d`.

`app.py`, `ranking.py`, `state.py` and `github.py` are untouched by this release.

## Edge cases

| Case | Behaviour |
|---|---|
| No repos configured | No summary, no rows |
| Every project at 0 commits | `0 commits`, empty bars, stakes bar hidden |
| `commits_7d` is `null` (activity call failed) | Row shows `—`, draws no bar, excluded from the week total and the stakes split. Never rendered as zero — "we could not ask" and "it did nothing" are different facts |
| All activity unknown | `activity unknown`, no bars, no stakes bar |
| No project has steps | Ring hidden, completion segment omitted |
| Board has no hero | Summary then tail, no hero card |

## Tests

DOM-stub-under-Node, the pattern the panel already uses. Harness lives outside
the repo.

- 11 repos with a hero and no rescue → 1 hero card + 10 tail rows; every project appears exactly once
- 11 repos with a hero and a rescue → 1 hero + 1 rescue + 9 tail rows; still exactly once each
- Ring `stroke-dashoffset` equals `251.3 × (1 − done/total)` for a known fraction
- Ring hidden when no project has steps
- `commits_7d: null` → `—`, no bar, excluded from the week total and stakes split
- All-zero portfolio → `0 commits`, no crash, stakes bar absent
- Pace: `commits_30d = 9` → no arrow; `= 10` with ratio 1.3 → `↑`; ratio 0.5 → `↓`;
  ratio 1.0 → nothing; boundaries exact at 1.25 and 0.6
- Summary line omits `idle` / `blocked` / `stale` when zero, includes each when
  non-zero
- Idle counts a project with a `[>]` and ≤2 commits; excludes one at 5/5 with no
  `[>]`; excludes one with `commits_7d: null`
- Markup in a project name lands only as `textContent`, never a parsed element
- Tapping a row toggles its expansion, as in 0.4.0
- Every colour token is defined on bare `:root` and only overridden inside the
  media query — no literal that works in one theme alone

## Rollout

Version **0.5.0**. The API is unchanged; the panel's surface is materially
different.

`DOCS.md` gains a short section on the dashboard, including the pace formula and
its volume floor so the arrows are explicable rather than magic, and a note that
the panel follows the device's light/dark setting.

## Decisions made

- Bars, not pies — measured, not assumed — approved
- Summary replaces the four stat tiles — approved
- Summary and tail merged into one list, deleting the top-five cut, the group
  row, the hero-pinning rule and the chart-to-card navigation — approved
- Pace arrows, stakes split, completion ring, idle count all included — approved
- Argus token file adopted verbatim rather than approximated — approved
- Halo as night, Daylight as day, switched by `prefers-color-scheme` — approved
- Manual theme override rejected: it would require persistence, and the panel is
  barred from `localStorage` — approved
- Concentration ratio and trend-over-time excluded — approved
