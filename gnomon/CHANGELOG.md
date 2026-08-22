# Changelog

## 0.5.1

The expanded card explains its position on the board.

- A momentum-ranked card now reads `momentum 154 - 18 this week, 100 this
  month` instead of restating the week's count, so a quieter week outranking a
  busier one is legible rather than mysterious
- The collapsed row is unchanged — still `18/wk`, the honest at-a-glance number
- Backend only. No panel change and no new API calls

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

## 0.4.0

The board is ordered by what you are actually working on.

- Ordering is now two-tier: a target within 30 days comes first, everything
  else by momentum
- Momentum is derived from commit activity — `(commits in 7d x 3) + commits in
  30d` — so it needs no maintenance and cannot go stale
- Debt (staleness, blocker, overdue) marks a card and picks the rescue slot,
  but never affects its position. Stale cards are no longer promoted and dimmed
  at the same time
- One hero card leads with its current step as the largest text on screen
- One optional rescue slot surfaces the most-owed project from below the fold,
  and renders nothing when nothing qualifies
- `score`, `score_factors` and `priority` are gone; `momentum`, `debt`,
  `debt_reason`, `role`, `order_reason`, `order_badge`, `commits_7d` and
  `commits_30d` replace them
- A vanished `target`, `stakes` or `phase` is now surfaced as a note
- Three GitHub calls per repo instead of two. A failed activity call reads as
  unknown, never as zero
- The backend is four modules; tests run without the container
- No STATE.md needs editing

## 0.3.1

Makes the sort explain itself. The board was ordered by a score it never showed.

- Every card now displays its score, so the ordering is visible as a number
  rather than something you have to take on faith
- Expanding a card shows the arithmetic behind it — `revenue 4.0 x 12d left 2.4
  = 9.6 high, rank 2 of 11` — including the blocked and parked multipliers
  when they apply
- New `score_factors` field per card: the labelled multipliers, in the order
  applied. `compute_score` now multiplies exactly these, so the reasoning shown
  can never disagree with the number that sorted it
- A test asserts the factors reconcile with the score for every acceptance case
- No change to the sort, the scoring weights, or any resulting order

## 0.3.0

Reads the `steps` list, and the panel becomes a roadmap rather than a single line.

- Parses `steps` from the header: `[x]` done, `[>]` current, `[ ]` todo
- `next` is now derived from the `[>]` step. The field name is unchanged, so
  anything reading it keeps working
- Legacy headers still render: a repo with a `next` string and no `steps` is
  used as-is
- Each card carries `steps`, `steps_done` and `steps_total`
- Tolerates a missing `steps` key, an empty list, unrecognised prefixes
  (kept verbatim, treated as todo), more than one `[>]` (first wins) and
  non-text entries — each surfaced as a note rather than a failure
- Panel rewritten: segmented per-step progress bar, tap a card to expand the
  full step list, state-coloured accent, stat tiles for high / blocked /
  stale / tracked
- Fixes the 0.2.0 regression where every card rendered empty, because the
  seeded headers carry `steps` and no `next`

## 0.2.0

**Breaking header change.** The `STATE.md` front-matter schema is not backward
compatible. Existing headers keep rendering, but `updated` is ignored and the
three new fields fall back to their defaults until you backfill them.

- Schema goes from four fields to six: `project`, `phase`, `stakes`, `target`,
  `next`, `blocker`
- `updated` removed from the header — freshness is now derived from the repo's
  `pushed_at` timestamp, so it can no longer drift out of date
- `priority` is computed from `stakes`, `target`, `blocker` and `phase` rather
  than stored, and is exposed as both a `score` and a `high`/`normal`/`low` band
- Sort is now priority-descending with age as a tiebreak, replacing the old
  problems-first order — blocked work gets a 1.4× multiplier and surfaces on
  its own merits
- New `parked` card state for projects deliberately set down
- Each repo now costs two GitHub calls per cycle: metadata plus `STATE.md`
- Distinct notes for 401, 403 and 404 on the metadata call, so a bad token
  reads differently from a misspelled repo name
- Options are re-read on every poll cycle — changing configuration no longer
  requires restarting the add-on
- `api/projects` gains `phase`, `stakes`, `target`, `days_to_target`,
  `priority` and `score` per card, plus a `phases` list on the response

## 0.1.0

Initial release.

- Polls GitHub for `STATE.md` in each configured repo
- Parses a four-field front-matter header: `project`, `next`, `blocker`, `updated`
- Ingress panel, sorted problems-first (blocked → stale → aging → fresh)
- Configurable poll interval and stale threshold
- Read-only; write-back deferred to v2
