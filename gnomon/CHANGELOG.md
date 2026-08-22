# Changelog

## 0.5.8

A theme switch, a version in the footer, and the month's shape on top.

- The header gains a three-way switch: auto, day, night. Auto follows the phone
  as it always did; the other two override it
- The choice is stored by the add-on in /data, not in the browser, so the panel
  stays barred from localStorage and the setting survives a reinstall
- The activity panel now leads the board, above the now panel: the shape of the
  month sets the context, then the instruction answers it
- The now panel no longer repeats the week's commit total, which the panel
  above it now carries. Its triage counts stay, since nothing else reports them
- When no repository reports activity at all, the board says "activity unknown"
  instead of drawing nothing, which would read as a quiet month
- The footer carries the running version, read from the add-on config so there
  is still only one place that declares it

## 0.5.7

The board says how the month is going, in words before numbers.

- A new activity panel sits under the now panel: the reading first — "your
  quietest week in four" — then four weekly bars carrying their own counts,
  then the four-week average as the baseline
- Four whole weeks are bucketed from the commit payload already fetched, so
  there is no extra API call and every bar is a full week
- Four near-identical weeks read "holding steady" instead of being ranked.
  Calling one of them the quietest is true and misleading at once
- The comparison is against the four-week average rather than last week alone,
  which one freak week could otherwise distort
- The completion ring and the stakes split are back, inside the new panel. The
  ring now carries role="img" so screen readers announce it, and the stakes key
  gained colour swatches so it finally legends its own bar

## 0.5.6

A deadline leads the board only when it actually needs you.

- Having a date used to be enough to take the top slot, so one dated project
  held it indefinitely and the best position on the screen became wallpaper. A
  dated project now leads when it is overdue, inside its final week, dormant,
  or visibly decelerating, and yields to momentum otherwise
- Only a project that can positively be seen holding its pace is demoted.
  Unreadable activity, no commits at all, and a silent pace arrow all count as
  at risk — the arrow says nothing below ten commits a month, which is exactly
  where a dormant project with a date approaching would hide
- A dated project that yields the top slot is never lost. The now panel gained
  a line naming what it is not showing: the on-track deadline, or failing that
  the runner-up
- When momentum leads, the date is still reported, after the commit counts
  rather than ahead of them
- Removed the order badge, which nothing has rendered since the summary and
  hero panels merged

## 0.5.5

The top of the board tells you what to do instead of how busy you were.

- The summary panel and the hero card are now one block. It leads with the
  instruction, then the project and the reading behind it in words — "slowing
  into a deadline" — then days left, steps left, and the rate
- The rate names last week beside it: `2/wk down, was 6/wk`. An arrow on its own
  never said how much it had slowed by
- The week is demoted to a strip at the foot: total commits, then counts of what
  is shipping soon, stalled and asleep. A count of zero is not drawn
- The completion ring and the stakes split are gone. Every number in the old
  summary was true and none of them changed what to do next
- The sidebar icon is fixed. `mdi:sundial` does not exist in Material Design
  Icons, so Home Assistant drew nothing at all; it is now `mdi:sun-angle`

## 0.5.4

The rescue slot surfaces work that stopped, not projects that are asleep.

- Rescue is chosen by stall — the commits a project was walked away from —
  instead of by debt. Debt is essentially age, and the longest-untouched
  projects are usually the ones untouched on purpose, so a seasonal tool asleep
  all summer used to outrank a project that died mid-flight
- A project counts as stalled when it has no commits in the last week but three
  or more in the last month. Absence of work is not debt; work that stopped is
- The rescue card now leads with what is at stake — `18 commits, then nothing
  for 11 days` — rather than how long it has been quiet
- Blocked projects are no longer rescued. A blocker is not cleared by working
  harder, and the card already shows it
- Deadline-tier cards are no longer rescued either; they are at the top of the
  board already
- Rank no longer disqualifies a candidate. The old rule looked only at cards
  ranked 5th or lower, which was a proxy for "not already visible"
- The slot renders nothing when nothing qualifies, which is most of the time

## 0.5.3

Maintaining the board no longer makes a project look worked on.

- Freshness is now days since the last real code commit, not days since the
  last push. A push carrying only a STATE.md edit reset the age, so every
  dormant project that had been given a status header reported as freshly
  worked
- Momentum ignores status commits. A second commits call lists what touched
  STATE.md and those commits are subtracted, so a seasonal project sitting at
  one seeded header now reads 0/wk rather than 1/wk
- A project with no code anywhere in the 30-day window reads `no code in 30+
  days` — a lower bound, never a fabricated precise age
- A commit that bundles STATE.md with real code counts as bookkeeping, so an
  active project undercounts by roughly one commit per session. Deliberate: the
  alternative is a dormant project reporting activity it does not have
- Four GitHub calls per repo per cycle instead of three, about 192 an hour
  against a 5,000 limit

## 0.5.2

The hero explains its own pace, and the footer stops repeating itself.

- A card ranked by its deadline now carries the momentum arithmetic too, so the
  hero reads `ships in 11 days - momentum 31 - 2 this week, 25 this month`. It
  was the only card on the board whose momentum was never spelled out
- Unknown activity adds no momentum clause at all rather than reporting a
  momentum of 0, which would be a different fact
- A project with a deadline and genuinely no commits reads `quiet for 40 days`
  instead of `momentum 0 - 0 this week, 0 this month`
- The expanded footer no longer states overdue, or a quiet stretch, twice at
  opposite ends of the same line

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
