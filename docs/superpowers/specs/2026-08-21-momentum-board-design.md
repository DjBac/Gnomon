# Momentum board — design

**Status:** approved 2026-08-21 · target release 0.4.0

## The problem

The board orders eleven projects by a score computed from `stakes` and `target`.
Measured against the real portfolio, every input is degenerate:

| Field | Distinct values across 11 repos | Most common |
|---|---|---|
| `stakes` | 3 | `personal` ×6 |
| `phase` | 3 | `usable` ×7 |
| `target` | 2 | none ×10 |
| `blocker` | 2 | none ×9 |
| age band | 1 | fresh ×11 |
| has `[>]` | 2 | yes ×10 |

Six repos tie at exactly 1.0. Argus — live in production, worked on daily —
scores identically to a finished, dormant beach-lounger booker. The sort is not
broken; it is ordering eleven things it has been told are near-identical.

Two further faults:

- **Position contradicts colour.** Stale and parked cards render at 55% opacity,
  yet the age tiebreak pushes them *up*. The board dims a card and promotes it in
  the same breath — a leftover from the problems-first ordering that 0.2.0
  replaced but never finished removing.
- **The maintained field is not the one being used.** Ten of eleven repos keep
  `[>]` current; one of eleven has a `target`. `[>]` is a by-product of working;
  `target` is homework. The scoring model leans on the field that rots.

## Goal

One hero card answering "what do I do now", a calm ordered tail below it, and
nothing that requires new hand-maintained fields.

The board optimises for **task initiation**, not for audit completeness. That is
a deliberate trade: worse at "review everything", better at "start working".

### Non-goals

- No new fields in `STATE.md`. Zero migration across the eleven repos.
- No alarm-first framing. Opening to "six things are rotting" is corrosive when
  under-delivery is already the sore point.
- No write-back. The board stays read-only.

## The engine

### Momentum — derived, never typed

Commit activity is the only signal in the portfolio with real information
content: 9 distinct values across 11 repos, range 1–100, against 1–3 for every
existing field. It tracks reality without anyone typing anything.

```
momentum = (commits in last 7 days x 3) + (commits in last 30 days)
```

One API call per repo yields both counts. The 30-day window **includes** the
7-day one, so recent commits are counted four times over — that overlap is the
weighting, not a bug. The 7-day term makes the board responsive to current work;
the 30-day term stops a quiet week from zeroing an active project.

### Ordering — two tiers, no magic arithmetic

1. **Deadline tier** — a `target` within 30 days, or overdue. Sorted by soonest
   first.
2. **Everything else** — by `momentum` descending.

A real deadline beats momentum; momentum beats everything else. `stakes` is the
final tiebreak only.

This is why `anthonyvenitis.com` is the hero at 2 commits/week: it ships in
twelve days, and that is precisely when the board should say so.

### Debt — marks, never positions

```
debt = age / stale_days  +  1.5 if blocked  +  2.0 if overdue
```

Debt never affects ordering. It marks the card and selects the rescue slot.
This is what resolves the position-versus-colour contradiction.

**Rescue floor: `debt >= 1.0`** — one full `stale_days` period of neglect, or a
blocker, or an overdue target. Below that, nothing is wrong enough to interrupt
for.

Note for the first release: seeding status headers into ten repos on one day
reset every `pushed_at`, so all ages currently read ~4 days and no repo clears
the floor on staleness alone. Expect the rescue slot to be absent, or driven only
by blockers, until real ages recover. That is correct behaviour, not a failure.

### Roles

- **hero** — first card of the ordered list. Suppressed entirely only when
  **all three** are true of that card: no `[>]`, no target within 30 days, and
  `momentum` is `0`. Unknown momentum (`None`) does **not** suppress the hero —
  a failed API call must not blank the board. An honest quiet board beats a hero
  announcing nothing, but only when the board is genuinely quiet.
- **rescue** — the single highest-debt repo, subject to all three of: `debt >=
  1.0`, not `parked`, and **below the visible fold** — rank 5 or lower in the
  ordered list, because rescuing something already on screen is pointless. When
  nothing qualifies the slot does not render: no "all clear" card, no empty
  state. Silence is the reward.
- **tail** — everything else.

### What happens to the existing fields

| Field | New role |
|---|---|
| `target` | Full power, but only within 30 days — which is how it is already used |
| `blocker` | Feeds debt. No longer inflates score |
| `stakes` | Display, plus final tiebreak |
| `phase` | Display, except `parked`, which excludes a repo from hero and rescue |
| `steps` / `[>]` | Unchanged. The `[>]` is the hero's headline |

Nothing is removed from the schema.

## The surface

Illustrative — the rescue card below assumes ages have recovered past the floor;
on first release the slot will most likely be absent.

```
Gnomon                                23:14  Refresh

┌──────────────────────────────────────────┐
│ anthonyvenitis.com          SHIPS 12d    │   HERO
│ ▇▇▇▇▇▇▇▇▇▇▇▇▇▇░░░░░░  5/7                │
│                                          │
│ Drafting quality for venues              │   the [>], largest
│ nobody has visited                       │   text on screen
│                                          │
│ revenue · usable · 2 commits/wk          │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│ ◈ NEEDS RESCUE                           │   only when earned
│ Oikovis Pulse · quiet 94 days            │
│ Release workflow that ships a bundle     │
└──────────────────────────────────────────┘

Argus                  51/wk   6/9   ▇▇▇▇▇░     TAIL, compact
Nostos                 17/wk   3/7   ▇▇░░░░
Nima                   29/wk   4/9   ▇▇▇░░░
...
```

- **Hero** — the `[>]` step carries the typographic weight, not the project name.
  Task initiation is the expensive part, so the thing you would actually *do* is
  the largest text. A badge states why it leads: `SHIPS 12d` or `51/wk`.
- **Rescue** — quieter than the hero, marked, with its reason in four words
  (*quiet 94 days*, *blocked*, *18d overdue*) and its `[>]`, so acting is one tap.
- **Tail** — name, activity (`51/wk` or `quiet`), progress fraction and bar,
  dimmed. Tap to expand into the full step list plus `order_reason`. Stale and
  parked stay at 55% opacity.
- **Stat tiles** become **Active · Blocked · Stale · Tracked**, where active means
  any commit in 7 days. `HIGH` is no longer a concept.

### Edge cases

- **No hero** — top card has nothing in flight, no near target, no momentum. The
  board opens with the tail.
- **Everything dormant** — no hero, rescue present, tail dimmed. The board should
  look asleep when you are.

## Data model

| | Fields |
|---|---|
| **Removed** | `score`, `score_factors`, `priority` |
| **Added** | `commits_7d`, `commits_30d`, `momentum`, `debt`, `debt_reason`, `role`, `order_reason` |
| **Unchanged** | `repo`, `project`, `phase`, `stakes`, `target`, `days_to_target`, `next`, `steps`, `steps_done`, `steps_total`, `blocker`, `updated`, `age`, `state`, `note` |

`order_reason` is produced by the same function that decides ordering, so the
explanation on a card can never disagree with its position. This carries forward
the 0.3.1 rule. It is a short phrase, and the hero badge is its compact form:

| Situation | `order_reason` | Badge |
|---|---|---|
| Deadline tier | `ships in 12 days` | `SHIPS 12d` |
| Momentum tier | `51 commits this week` | `51/wk` |
| No commits in 30d | `quiet for 94 days` | `quiet` |
| Commits call failed | `activity unknown` | `—` |

Response envelope is unchanged: `projects`, `fetched`, `stale_days`, `phases`,
`error`.

## Error handling

**Unknown is not zero.** If the commits call fails, `momentum` is `None`, not
`0`. A network blip must never make the most active project look dormant and sink
it. Unknown momentum sorts as if quiet but renders "activity unknown" and adds a
note, so persistent failure is visible rather than silently wrong.

The 100-commit page cap means very active repos saturate. Acceptable: past 100
commits a month, "very active" is the whole answer.

Existing 401 / 403 / 404 / malformed-YAML handling is unchanged.

### Vanished-field detection

A previously-set `target`, `stakes` or `phase` can disappear when a session
rewrites a header. This happened: Nostos silently lost `target: 2027-09-30`, and
the board had no way to show a field that no longer existed.

Persist last-seen `target` / `stakes` / `phase` per repo in `/data`. When a
previously-set value becomes absent, surface it as a note on the card. Bounded
to those three fields and roughly twenty lines plus a small state file.

## Code structure

`app.py` is 598 lines doing eight jobs, and this feature adds roughly 150 more.
Split it:

```
state.py     header parsing — front-matter, steps, normalisation, dates
github.py    the three API calls, error notes
ranking.py   momentum, debt, ordering, roles, reasons
app.py       options, card assembly, HTTP routes, startup
```

**Required consequence:** the Dockerfile does `COPY app.py /app/app.py`. It must
become `COPY *.py /app/`. This is the only change to a previously off-limits
file, and it is unavoidable given the split.

No new dependencies. `aiohttp` and `PyYAML` only.

## API cost

Three calls per repo — metadata, `STATE.md`, `commits?since=30d&per_page=100` —
against two today. Eleven repos every 15 minutes is 132 calls/hour against a
5,000/hour limit.

## Tests

All in the existing dependency-free `--selftest` pattern.

- The 8 step-parser cases, unchanged
- The 7 priority cases retire with the score
- Momentum arithmetic
- Deadline beats momentum
- Momentum orders the non-deadline tier
- `parked` excluded from hero and rescue
- Debt floor respected
- Rescue must come from below the fold
- Rescue absent when nothing qualifies
- `momentum=None` behaves differently from `momentum=0`
- **Golden order** — the eleven real headers produce the approved order

## Rollout

Version **0.4.0**. The API shape changes, so this is a minor bump.

Zero migration: no `STATE.md` in any repo needs editing.

`DOCS.md` must state plainly that **waiting on yourself is not a blocker** —
Nostos currently reads `blocker: "Today bake-off walk — Anthony"`, which is an
own-action, not an external dependency. Under this design the misuse is cheap
(blocker no longer inflates score) but it still pollutes debt and the rescue slot.

## Decisions made

- Momentum drives ordering; a near deadline overrides it — approved
- Debt marks and rescues but never positions — approved
- One rescue slot, from below the fold, absent when unearned — approved
- The `[>]` outranks the project name typographically on the hero — approved
- Vanished-field detection included in 0.4.0 rather than deferred — approved
