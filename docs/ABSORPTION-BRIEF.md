# Absorption brief — everything Argus needs to know about Gnomon

Written 2026-08-22, on Anthony's decision that **Argus absorbs Gnomon entirely**:
the Home Assistant add-on is retired, Gnomon becomes a Projects view inside
Argus fed by a collector plugin.

This document exists so Argus does not have to reverse-engineer eight releases
of judgment from a chat message. Read `docs/HANDOFF.md` for the current shape of
the running system; this file is specifically about what crosses over.

Gnomon is at **0.5.8**, deployed, 188 assertions passing.

---

## 1 · What Gnomon is, and the one rule that governs it

A read-only board that polls a list of GitHub repositories, reads the YAML
front-matter at the top of each repo's `STATE.md`, and ranks the projects by
what deserves attention.

**The governing rule: facts come from the GitHub API, judgments come from
`STATE.md`.** Anything derivable is derived. Nothing that can rot by hand is
stored by hand. Every design argument in this project has been settled by
applying it.

---

## 2 · The STATE.md schema — this is the contract, and it does not change

Every tracked repository carries this block at the very top of `STATE.md`:

```yaml
---
project: Argus
phase: usable
stakes: personal
target: ""
blocker: ""
steps:
  - "[x] Seven collectors live, incl. Veeam and per-guest"
  - "[>] UniFi, cameras, home health view, Bridge, and the rest"
---
```

| Field | Meaning |
|---|---|
| `project` | Display name |
| `phase` | `idea` / `building` / `usable` / `shipped` / `parked` |
| `stakes` | `revenue` / `product` / `personal` — orders ties, and splits the week |
| `target` | ISO date or `""`. Unparseable values are dropped **silently** — a known defect |
| `blocker` | Free text. Non-empty means something *external* is stopping progress |
| `steps` | Ordered outcomes. `[x]` done, `[>]` current (at most one), `[ ]` to do |

`updated` is **not** a field — freshness is derived. That was deliberate: a
hand-maintained date is a date that lies.

**Argus's own `STATE.md` already carries this header** and is read by Gnomon
today. After absorption Argus reads its own status file, which is odd but
harmless — worth knowing before someone reports it as a bug.

---

## 3 · What crosses over, and what dies

| File | Lines | Fate |
|---|---|---|
| `gnomon/ranking.py` | 473 | **Ports unchanged.** stdlib only |
| `gnomon/state.py` | 169 | **Ports unchanged.** `yaml` + stdlib |
| `gnomon/github.py` | 87 | **Becomes a collector.** Already async, already isolates failures |
| `gnomon/app.py` | 405 | Discard. Options, routes, `/data` persistence — Argus has its own |
| `gnomon/www/index.html` | 1288 | Discard. Replaced by the Projects view |
| `gnomon/selftest.py` | 1123 | **Port the assertions.** 188 of them, no test framework, plain functions |

`ranking.py` and `state.py` have a standing rule that they must never import
`aiohttp`. It was written so the suite could run outside the container on
Anthony's Mac. The accidental consequence is that they are already portable —
they have no I/O, no framework and no network, and they drop into Argus as-is.

---

## 4 · The rules, precisely

**Momentum** — `commits_7d * 3 + commits_30d`. The windows overlap, so a commit
this week is worth 4 and one from 8–30 days ago is worth 1. Default branch only.

**Ordering** — two tiers. At-risk deadlines first, soonest first; then momentum
descending; ties on stakes (revenue, product, personal), then repo name.

**At risk** (`ranking.at_risk`) — a dated project leads only when it is overdue,
inside its final 7 days, dormant, or visibly decelerating. Otherwise momentum
decides. **Only a project that can positively be seen holding its pace is
demoted** — unreadable activity, zero commits, and a silent pace arrow all count
as at risk. Having a date is not the same as needing attention.

**Stall** (`ranking.stall`) — `commits_30d` when `commits_7d == 0` and the month
clears a floor of 3, else 0. Read it as *commits walked away from*. This is what
selects the rescue slot.

**Debt** — `age / stale_days + 1.5 if blocked + 2.0 if overdue`. **Debt marks a
card and never moves one.** Two tests defend this: `selftest_debt_never_orders`
and `selftest_debt_never_rescues`. Both exist because the mistake was made:
debt is essentially age, and the longest-untouched projects are the ones
untouched on purpose, so debt-driven selection surfaces a seasonal tool asleep
all summer over a project that died mid-flight.

**Pace** — `commits_7d / (commits_30d / 4.3)`; up at ≥1.25, down at ≤0.6,
**silent below 10 commits a month**, where a single commit reads as a 4.3×
surge.

**Classification** — blocker → `blocked`; `phase: parked` → `parked`; unknown
age → `unknown`; ≤6 days → `fresh`; ≤`stale_days` → `aging`; else `stale`.

---

## 5 · The invariants — break these and you reintroduce shipped bugs

**Unknown is not zero.** `commits_7d`, `commits_30d` and `momentum` are `null`
when the activity call fails. That is different from a genuinely quiet project.
**Three separate bugs came from collapsing them.** Any code touching activity
must preserve the distinction — including in reverse: a failed call is not
reassurance either, which is why `at_risk` returns true when it cannot read the
pace.

**Status commits are not work.** `pushed_at` is repo-level and any push resets
it, so a one-line `STATE.md` edit made every dormant project look freshly
worked — *feeding the board corrupted the board*. Fixed in 0.5.3 by a second
commits call with `path=STATE.md` and subtracting those SHAs. A commit bundling
STATE.md with real code is dropped too, so active projects undercount by roughly
one per session while dormant ones collapse to exactly zero. That asymmetry is
deliberate.

**A floor is not a measurement.** With no code anywhere in the 30-day window,
age is set to 30 with `age_is_floor` true and every string reads `30+ days`.
Never render a floored value as precise.

**Nothing is stated twice.** `ranking.why_line` drops a `debt_reason` that would
only restate the rank explanation. Overdue and quiet were each being reported at
both ends of one line.

---

## 6 · Configuration that has to move

| Today | Notes |
|---|---|
| `github_token` | Fine-grained PAT. **Single-owner**: `Oikovis/pulse` is public but 404s because the token is scoped to `DjBac`. Not fixable with one token |
| `repos` | 12 configured, 10 reporting. `portolan` is local-only and has no `STATE.md` |
| `stale_days` | Default 14 |
| `poll_minutes` | Default 15 |
| `/data/gnomon-seen.json` | Vanished-field memory — what each repo's `phase`/`stakes`/`target` was last poll, so a field disappearing can be reported. **Needs a home in Argus** |
| `/data/gnomon-theme.json` | Panel theme choice. Dies with the panel |

**Four GitHub calls per repo per cycle** — repo metadata, `STATE.md` contents,
commits, and commits filtered to `path=STATE.md`. About 192/hour for 12 repos
against a 5,000/hour limit.

---

## 7 · What Argus makes possible that the panel never could

Gnomon has no memory beyond `seen`, no history, and cannot tell you anything —
it can only be checked. Argus has `chronicle.py`, `events/` with migrations,
`alerts/{engine,machine,notify}`, and a metrics `series`. That unlocks:

1. **Honest forecasting.** Commits-per-step has no exchange rate and was
   refused. **Steps per week is directly measurable** once step completions are
   recorded, so "0.6 steps a week, 2 left, finishes 15 September" is arithmetic.
2. **Slip history** — a `target` that has moved twice.
3. **Blocked-for** — how long a blocker has sat. 23 days needs escalating.
4. **Since you were away** — the Eye already knows; Projects can borrow it.
5. **Stakes drift** — "revenue under 15% for six weeks running".
6. **Focus** — projects touched this week versus last.

And the largest: **it can interrupt**. A stall or a slipping deadline pushed
through HA, landing in the Incident stance.

---

## 8 · Known defects, carried over

Full list in `docs/known-issues.md`. The ones that matter to a rewrite:

- **An unparseable `target` is dropped silently** while a *removed* one produces
  a note. `the-bridge` carries `target: "Poseidonia 2028"` and says nothing.
- **A present-but-unrecognised value reads as vanished** — `phase: wip`
  normalises to `""`, so the check reports it removed every poll, forever.
- **A `STATE.md` fetch failure overwrites the vanished-field snapshot.** Safe by
  consequence, not by design.
- **`premiere`'s `STATE.md` is 409 KB**, refetched whole every poll — ~38 MB/day.
- **The repo-name tiebreak is case-sensitive ASCII.**
- **`--unknown-c` reaches data-bearing surfaces** via `--accent`, so an
  unknown-state card's progress reads 0%. Panel-only; dies with the panel.

---

## 9 · Testing, honestly

`selftest.py` is 188 assertions, no framework, exits non-zero on failure. It
covers `state` and `ranking` only. **It has never covered the panel** — the
frontend was verified with throwaway DOM stubs in a scratchpad, and
`config.yaml` has no coverage at all, which is how `panel_icon: mdi:sundial`
shipped for months rendering a blank sidebar icon.

The suite's most valuable tests are the ones that exist because the mistake was
already made: `selftest_debt_never_orders`, `selftest_debt_never_rescues`, and
the checks that a stated number equals the number actually sorted on. Port those
first; they encode decisions, not behaviour.

**Gnomon has no automated colour check.** A rule in HANDOFF, plus a hand-run
grep with a positional carve-out. Argus's is better; Gnomon should adopt it, not
the reverse.

---

## 10 · Deploying, while both exist

Gnomon updates from this Mac via Home Assistant's Core API — the Supervisor
proxy 401s. `GET /api/states/update.gnomon_update`, then
`POST /api/services/update/install` with that entity. Credentials in
`~/Code/argus/.env` as `HA_URL` / `HA_TOKEN`.

The add-on stays running and supported until the Projects view is trusted.
Retirement is the last of the three phases, not the first.

---

## 11 · Appendix: the tuning constants

Every threshold in `ranking.py`, with the reasoning that is not obvious from the
value. These arrive with the file, but they look arbitrary without the reasons,
and someone will eventually be tempted to "round them off".

| Constant | Value | Why that number |
|---|---|---|
| `FRESH_MAX` | 6 | A project touched within the last six days is fresh; day seven begins aging |
| `MOMENTUM_RECENT_DAYS` | 7 | The recent window |
| `MOMENTUM_PREVIOUS_DAYS` | 14 | The week before last, so a rate can name its predecessor |
| `MOMENTUM_WINDOW_DAYS` | 30 | The whole window, and the single `since` sent to the API |
| `RECENT_WEIGHT` | 3 | The windows **overlap**, so this makes a commit this week worth 4 and one from 8–30 days ago worth 1 |
| `WEEK_BUCKETS` | 4 | Four whole weeks is 28 days, which fits inside the 30-day window, so every bar is a full week |
| `STEADY_BAND` | 0.15 | Below 15% spread across four weeks, they are ranked "holding steady" rather than one being called quietest — true and misleading at once |
| `URGENT_DAYS` | 30 | A target beyond this is not mentioned at all |
| `FINAL_WEEK` | 7 | Inside its last week a dated project is at risk regardless of pace |
| `STALL_FLOOR` | 3 | One stray commit three weeks ago is not a stall worth surfacing |
| `BLOCKED_DEBT` | 1.5 | Debt only; **never affects ordering or rescue** |
| `OVERDUE_DEBT` | 2.0 | Same |
| `STAKES_ORDER` | revenue 0, product 1, personal 2 | Tie-break only |
| `PACE_WINDOW` | 4.3 | Weeks in 30 days |
| `PACE_FLOOR` | 10 | Below ten commits a month the arrow is **silent** — one commit reads as a 4.3× surge |
| `PACE_UP` / `PACE_DOWN` | 1.25 / 0.6 | Deliberately wide. Nothing between them gets an arrow |

---

## 12 · Appendix: role assignment, in full

`assign_roles` mutates a **sorted** list in place. Everything starts as `tail`.

**hero** — `ordered[0]`, unless suppressed. Suppressed only when all three hold:
no `[>]` step, no target within `URGENT_DAYS`, and momentum exactly `0`.
**Unknown momentum does not suppress it** — that is the invariant, not an
oversight.

**rescue** — at most one, and often none. A card is eligible only when *all* of:

- it is not the hero (you are already looking at it)
- `phase != "parked"`
- it has no blocker — a blocker is not cleared by working harder
- it is not in the deadline tier (`days_to_target <= URGENT_DAYS`) — that card
  is at the top of the board already
- `stall(card)` is truthy

Among eligible cards, selection is `min` over
`(-stall, age, STAKES_ORDER, repo)` — biggest abandonment first, ties to the
**warmer** stall, which is cheaper to restart and likelier to actually happen.

**Rank plays no part.** An earlier version required rank 5 or lower; that was a
proxy for "not already visible" and has been replaced by stating the real rule.

**tail** — everything else, in sort order.

---

## 13 · Appendix: the sentences are the product

The board's user-facing strings are not labels; they are eight releases of
judgment compressed into wording, and several were rewritten specifically to
stop them lying. The view is rebuilt, but these should survive it.

| Situation | The string |
|---|---|
| Momentum-ranked card | `momentum 154 - 18 this week, 100 this month` |
| At-risk deadline | `ships in 11 days · momentum 31 - 2 this week, 25 this month` |
| Deadline not at risk | `momentum 90 - 20 this week, 30 this month · ships in 24 days` |
| Overdue | `3 days overdue · momentum 12 - 1 this week, 9 this month` |
| Genuinely quiet, age known | `quiet for 40 days` |
| No code in the window | `no code in 30+ days` — a floor, never a precise age |
| Activity unreadable | `activity unknown` |
| Rescue | `18 commits, then nothing for 11 days` |
| Rate, always compared | `2/wk ↓ · was 6/wk` |
| Four-week reading | `Your quietest week in four` / `Holding steady` |

Two rules govern all of them. **A number that orders the board must appear on
the board** — the momentum sentence exists because the board sorted on a score
it never displayed. **A fact is stated once** — `why_line` suppresses a
`debt_reason` that would only restate the rank explanation.

---

## 14 · Appendix: one rendering gotcha that transfers

From Gnomon's panel constraints, and it applies directly to Argus's `Ring` and
`Sparkline`:

> `var()` does not resolve inside SVG **presentation attributes**.
> `stroke="var(--ok)"` renders an invisible ring **with no error**.
> Ring strokes must be set by CSS class.

It cost a release to find, because nothing warns — the ring simply is not there.
Argus's `Ring` already builds its circles with `setAttribute`, so anything the
Projects view adds to an SVG must colour through a class, never an attribute.

The other panel constraints (no `innerHTML`, relative fetch paths, no
`localStorage`) were Home Assistant ingress concerns and die with the add-on.
