# Activity dashboard — design

**Status:** approved 2026-08-21 · target release 0.5.0

## The problem

The panel's top surface is four stat tiles: Active, Blocked, Stale, Tracked. Two
of them currently read zero, a third duplicates what the activity labels on each
card already say, and the fourth is a constant. The strip occupies 70px and
answers nothing you could act on.

Below it the board answers "what should I do now" well. Nothing answers "where
did my time actually go, and is it going where it matters".

## What measurement decided

Every candidate visual was rendered against the real eleven-repo portfolio before
being chosen. This killed most of them.

**Pie charts are out.** The categorical fields are degenerate — the same finding
that killed the old ordering model:

| Pie of… | Reality |
|---|---|
| `state` | one solid circle — 11/11 fresh |
| `has target` | 91% one slice |
| `phase` | 64% one slice |
| `stakes` | 6 / 3 / 2 — the only one with shape |

**The continuous fields have real spread**, which is what bars are for:

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
over 30 days, 2 in the last 7. Nothing on the board says this. The hero card
shows `SHIPS 12d` and `2/WK` side by side and leaves the reader to notice the
tension.

Surfacing that class of fact is the point of this feature.

## Goal

Replace the four stat tiles with a dashboard that answers, in one glance: where
the week's effort went, whether each project is speeding up or slowing down,
whether effort matched stakes, and how much work remains.

### Non-goals

- **No new backend fields, no new API calls, no persistence.** Every number is
  computed in the browser from data the panel already receives.
- **No pie charts.** See above.
- **No filtering.** Hiding projects is the failure mode the board was designed
  against.
- **Do not displace the hero.** The hero card must still open above the fold on a
  375×812 iPhone. This is the binding constraint on everything below.

## The dashboard

```
THIS WEEK · 156 commits · 11 tracked

Argus                ████████████████████  58 ↑
Nima                 ██████████            29 ↑
The Bridge           ████████              23 ↑
Gnomon               ███████               20 ↑
Nostos               ██████                18
· anthonyvenitis.com ▏                      2 ↓
5 more · 6 commits                            ›

revenue ▎ product ██████ personal █████████
  13%       34%              53%

51 of 79 steps · 5 idle
```

### Header

`THIS WEEK · <total> commits · <count> tracked`, where total is the sum of
`commits_7d` across cards with known activity, and count is every card.

### Activity rows

Top five by `commits_7d` descending. Bar width is linear against the highest
`commits_7d` among cards with known activity, so the busiest repo is full width
and every other bar reads relative to it. Each row is a full-width tap target.

**The hero is always shown.** If the hero card is not already in the top five it
is pinned as an extra row directly below them, marked with a leading `·` so its
out-of-rank position is explained. Without this rule the most valuable pace
signal in the portfolio — a deadline project decelerating — lands inside the
collapsed group and is never seen. If the hero is suppressed (the board has no
hero) no row is pinned.

The pinned row is a normal activity row in every other respect — it draws a bar,
carries a pace arrow, and is tappable. It is **not** counted in the group row's
totals, since it is displayed rather than collapsed.

### The group row

Remaining projects collapse to `<n> more · <sum> commits`, carrying both the
count and their combined activity. `5 more · 6 commits` states the fact worth
seeing: nearly half the portfolio produced almost nothing this week. Collapsing
to `5 more` alone would hide it.

If only one project remains it renders as a normal row — a group of one is
noise.

### Pace arrows

```
ratio = commits_7d / (commits_30d / 4.3)
```

- `↑` when `ratio >= 1.25`
- `↓` when `ratio <= 0.6`
- nothing in between

**Suppressed entirely when `commits_30d < 10.`** Below that there is not enough
history to say anything, and a fabricated arrow is worse than no arrow.

The floor is load-bearing and does real work. Argus reads x4.3 because 58 of its
58 monthly commits landed this week — that is genuine acceleration and the arrow
is honest. Pilates Auto-Booker reads x4.3 off a single commit, which is noise.
Same ratio, opposite meanings, separated by volume alone.

### Stakes split

A single segmented bar: share of the week's commits by `stakes`, in fixed order
revenue / product / personal, each with its own colour and a percentage label.

This is the only place `stakes` does real work. The ordering model demoted it to
a final tiebreak because it cannot discriminate eleven projects; aggregated
across a week it is genuinely informative. Today it reads 13% / 34% / 53% —
thirteen percent of the week went to revenue work, and one of those two projects
ships in twelve days.

Hidden entirely when the week's total is zero, since shares of zero are
undefined.

### Footer line

`<done> of <total> steps` always, followed by conditional segments appended only
when non-zero:

- `<n> idle` — projects with a current step and `commits_7d <= 2`. This
  distinguishes quiet-because-finished from quiet-despite-intent: a project at
  5/5 with nothing in flight is correctly excluded, because it is neglecting
  nothing. A project whose `commits_7d` is `null` is **also excluded** — unknown
  activity is not evidence of inactivity, the same rule the ordering model
  follows.
- `<n> blocked`
- `<n> stale`

One line rather than three. Three stacked lines cost 50px for information that
reads better combined, and the height budget does not have 50px to spare.

## Interaction

**Tapping a project row** sets that card's expansion state, applies it, and
scrolls the card into view. The in-memory `open` map already survives re-renders,
so the card stays expanded through the 120-second refresh; that machinery is
reused rather than duplicated.

Scrolling honours `prefers-reduced-motion` — smooth when allowed, instant when
not. The panel's CSS already disables animation under that query, but
`scrollIntoView` ignores CSS and must check `matchMedia` itself.

**Tapping the group row** scrolls to the highest-ranked grouped project and
stops. No expansion, no mode. The chevron means "take me there", not "unfold a
panel", so there is no hidden state to get stuck in.

**The chart and the board are ordered differently, deliberately.** The board
ranks by deadline then momentum; the chart ranks by raw activity. Argus is chart
row 1 and board row 3. That is not an inconsistency to reconcile — the chart
shows where your hands went, the board shows where they should go, and tapping is
the bridge between the two answers.

## Data

Everything is derived in the browser from fields already on each card:
`project`, `repo`, `role`, `stakes`, `state`, `next`, `steps_done`,
`steps_total`, `commits_7d`, `commits_30d`.

No backend change. No new API calls. No new persistence. `app.py`, `ranking.py`,
`state.py` and `github.py` are untouched by this release.

## Edge cases

| Case | Behaviour |
|---|---|
| No repos configured | No dashboard renders |
| Every project at 0 commits | Header reads `0 commits`, bars render empty, stakes bar hidden |
| `commits_7d` is `null` (activity call failed) | Row shows `—`, draws no bar, excluded from the total and from the stakes split, sorted after known rows. Never folded into the group row — "we could not ask" and "it did nothing" are different facts |
| All activity unknown | Header reads `activity unknown`, no bars, no stakes bar |
| Six or fewer projects | All rows shown, no group row |
| Hero already in the top five | Not duplicated |
| Board has no hero | No pinned row |
| `steps_total` is 0 across all cards | Completion segment omitted from the footer |

## Integration

The static `<div class="tiles">` block is replaced by an empty `<div
id="summary">`. `tally(cards)` becomes `renderSummary(cards)`, called from the
same place with the same argument. `tally` and the four `t-*` element ids are
deleted.

`render()` is untouched — the dashboard lives outside `board` and does not
interact with card rendering.

New functions inside the existing IIFE, all returning DOM nodes: `renderSummary`,
`chartRow`, `groupRow`, `stakesBar`, `footerLine`, plus a `pace` helper returning
`"up"`, `"down"` or `""`.

**DOM construction only.** No `innerHTML`, no HTML string concatenation, no
escaping helper. Bars set `style.width` as a percentage. This matches the rest of
the file and is a project-wide constraint.

## Tests

DOM-stub-under-Node, the pattern the panel already uses. Harness lives outside
the repo.

- 11 repos → 5 rows, 1 pinned hero row, 1 group row reading `5 more · 6 commits`
- 6 repos → 6 rows, no group row
- Hero inside the top five → not duplicated, no pinned row
- No hero → no pinned row
- `commits_7d: null` → `—`, no bar, excluded from header total and stakes split
- All-zero portfolio → `0 commits`, no crash, stakes bar absent
- Pace: `commits_30d = 9` → no arrow; `= 10` with ratio 1.3 → `↑`; ratio 0.5 → `↓`;
  ratio 1.0 → nothing
- Pace boundaries exact at 1.25 and 0.6
- Footer omits `idle`, `blocked`, `stale` when zero; includes each when non-zero
- Idle counts a project with a `[>]` and 2 commits; excludes one at 5/5 with no
  `[>]`; excludes one with a `[>]` and `commits_7d: null`
- Markup in a project name lands only as `textContent`, never a parsed element
- Tapping a row calls `scrollIntoView` on the card with the matching `data-repo`
  and sets its open state
- Tapping the group row targets the highest-ranked grouped project and does not
  expand it

## Rollout

Version **0.5.0**. The API is unchanged; the panel's top surface is materially
different.

`DOCS.md` gains a short section describing the dashboard, including the pace
formula and its volume floor, so the arrows are explicable rather than magic.

## Decisions made

- Bars, not pies — measured, not assumed — approved
- Dashboard replaces the four stat tiles rather than sitting above them — approved
- Tapping a row scrolls to that card and expands it — approved
- Pace arrows, stakes split, completion, idle count all included — approved
- Hero pinned into the chart when outside the top five — approved
- Concentration ratio and trend-over-time excluded — approved
