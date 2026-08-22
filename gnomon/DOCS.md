# Gnomon

An at-a-glance project board. Polls your GitHub repositories, reads the YAML
front-matter block from each repo's `STATE.md`, and renders one line per project
in the Home Assistant sidebar.

Read-only. Editing from the panel is deliberately out of scope for v1.

## The contract

Every tracked repo needs a `STATE.md` beginning with exactly this block:

```yaml
---
project: Nostos
phase: building
stakes: revenue
target: 2027-09-30
blocker: ""
steps:
  - "[x] Branded delivery pages"
  - "[>] Wire Stripe webhook to delivery unlock"
  - "[ ] Timeline review UI"
---
```

Everything below the closing `---` is freeform — notes, decisions, scratch. The
header is the only part anything depends on.

| Field | Accepted values | If absent or unrecognised |
|---|---|---|
| `project` | free text | falls back to the repo name |
| `phase` | `idea`, `building`, `usable`, `shipped`, `parked` | empty |
| `stakes` | `revenue`, `product`, `personal` | `personal` |
| `target` | a date, or empty | no target — treated as not urgent |
| `blocker` | free text, an external dependency — empty means not blocked | empty |
| `steps` | a list of prefixed strings, see below | no roadmap on the card |

> **Waiting on yourself is not a blocker.** A blocker is an external dependency —
> a vendor key, someone else's review, an outage. Your own next action belongs in
> `steps` as the `[>]`. A blocker adds 1.5 to debt and can pull a project into
> the rescue slot, so mislabelling one costs you a real alert.

### Steps

`steps` is the roadmap. Each entry is a string beginning with one of three
prefixes:

| Prefix | Meaning |
|---|---|
| `[x] ` | done |
| `[>] ` | the current step — **at most one per repo** |
| `[ ] ` | not started |

```yaml
steps:
  - "[x] Branded delivery pages"
  - "[>] Wire Stripe webhook to delivery unlock"
  - "[ ] Timeline review UI"
```

**Every entry must be double-quoted.** An unquoted `[x]` opens a YAML flow
sequence and the file will not parse.

Write steps as outcomes rather than tasks — "Timeline review UI", not "refactor
the player" — and keep each under about 60 characters so it fits a phone-width
card. Fewer real steps beat a padded list.

The parser is deliberately forgiving, because a header that fails is worse than
a header that is slightly wrong. An unrecognised prefix is kept verbatim and
treated as todo; if more than one `[>]` appears the first wins and the rest
become todo; a missing key, an empty list, a non-list value and non-text
entries all yield an empty roadmap and a note on the card. None of them take
the board down.

### `next` is derived, not written

There is no `next` field any more — the current action is whichever step
carries `[>]`. The API still exposes `next` on each card, now holding that
step's text, so nothing downstream had to change.

A repo that still uses the old `next` string and has no `steps` renders from
it unchanged. Old headers keep working; they simply show no progress bar.

Unknown keys are ignored rather than rejected, so a repo can carry extra header
fields for its own purposes. Malformed YAML is caught and surfaced as a note on
the card — it never takes the board down.

### A vanished field is a note, not silence

The backend remembers `target`, `stakes` and `phase` between polls. If one of
them held a value last time and holds none this time — someone deleted a
`target` line rather than clearing it to a recognised default, say — the next
poll surfaces a note (`"target removed from STATE.md"`) instead of quietly
reverting to the field's default as if it had never been set. The note keeps
showing on every subsequent poll until the field returns; it only fires on
a value disappearing, never on one merely changing.

### Two fields that are deliberately absent

`updated` used to be a field. It is now derived from the repo's `pushed_at`
timestamp via the GitHub API. A hand-maintained freshness date is the one field
guaranteed to be wrong exactly when it matters, because the moment you stop
touching a project is also the moment you stop updating its header.

Nothing about a card's position on the board is stored either. Order is
recomputed on every poll from `target`, commit activity and `stakes` — see
below. A stored ranking is a judgment frozen at the time of writing; a
computed one moves on its own as a deadline approaches or a project goes
quiet.

The rule behind both: facts come from the GitHub API, judgments come from
`STATE.md`. Anything derivable is derived.

## How the board is ordered

Ordering is two-tier.

**Tier 1 — deadline.** Any card with a `target` at most 30 days away —
including one already overdue — comes first, soonest (or most overdue) first.

**Tier 2 — momentum.** Every other card is ordered by momentum, descending:

```
momentum = (commits in the last 7 days × 3) + commits in the last 30 days
```

Momentum comes entirely from the GitHub commits API. Nothing in `STATE.md`
feeds it, so it needs no maintenance and cannot drift the way a hand-typed
field can. `commits_7d` and `commits_30d` are exposed on every card so the
number behind the weighting is never hidden. A card whose activity call
failed carries `momentum: null` — it sorts alongside cards with genuinely
zero momentum (never below them), but it is never displayed or reasoned
about as if it were confirmed quiet. Unknown and zero look the same to the
sort key; they do not look the same on the card.

Momentum counts commits on the repository's **default branch only** — the
commits call is made with no `sha`, so work sitting on an unmerged feature
branch raises it not at all, even though the repo's `pushed_at` still counts
that push as fresh activity for the freshness colour.

If momentum ties, `stakes` breaks it — `revenue`, then `product`, then
`personal` — and if that also ties, the repo name settles it. `stakes` is
purely a tiebreak now; it no longer sets a base weight.

### Debt marks a card. It never moves one.

`debt` is a separate number that plays no part in the sort:

```
debt = age / stale_days
     + 1.5  if blocker is non-empty
     + 2.0  if the target is overdue
```

Debt drives exactly two things: the `debt_reason` shown on a card (`"quiet 94
days"`, `"blocked"`, `"3d overdue"`), and which single card — if any —
receives the rescue slot below. It is never read by the sort key. A project
can carry a debt of 9.0 and still sit exactly where its tier and momentum put
it; a stale or blocked project used to get quietly promoted by the old score,
which buried the very cards that most needed a visible flag.

### Roles: hero, rescue, tail

Every card carries a `role`.

- **`hero`** — the top card after sorting. It leads with its current step
  rendered as the largest text on the board. It only steps aside for `tail`
  styling when the top card has nothing to say at all: no current step, no
  deadline inside 30 days, and momentum of exactly `0`. Unknown momentum does
  not suppress it — "we could not find out" is not the same as "nothing is
  happening", and only the latter empties the hero slot.
- **`rescue`** — at most one card. The candidate pool is every card ranked
  5th or lower, excluding anything `parked`, with `debt >= 1.0`. Whichever
  candidate carries the most debt gets the slot. A project that already sits
  in the top four is never rescued, however much debt it carries — it does
  not need surfacing, it is already visible. If the pool is empty, no card
  is `rescue` and the panel renders no rescue slot at all.
- **`tail`** — everything else, in sort order.

### The golden order

This is the order today's eleven-repo portfolio produces. It is exercised by
the test suite as a regression check, so a future change to the formula
cannot silently reshuffle the board:

| Rank | Repo | Stakes | Deadline | Momentum | Debt | Role |
|---|---|---|---|---|---|---|
| 1 | anthonyvenitis | revenue | 12d | 31 | 0.29 | hero |
| 2 | argus | personal | — | 204 | 0.00 | tail |
| 3 | premiere | revenue | — | 151 | 1.79 | tail |
| 4 | nima | product | — | 139 | 0.29 | tail |
| 5 | the-bridge | product | — | 88 | 1.57 | rescue |
| 6 | oikovis-autom | personal | — | 21 | 0.29 | tail |
| 7 | Gnomon | personal | — | 19 | 0.00 | tail |
| 8 | pounta | personal | — | 11 | 0.29 | tail |
| 9 | pulse | product | — | 4 | 0.29 | tail |
| 10 | ha-doukas-bus | personal | — | 4 | 0.29 | tail |
| 11 | pilates | personal | — | 4 | 0.29 | tail |

Two things worth noticing in that table. `premiere` carries more debt than
`the-bridge` (1.79 vs 1.57) and is blocked, yet it is not rescued — it
already sits at rank 3, above the rank-5 floor, so `the-bridge` gets the slot
instead. And `pulse`, `ha-doukas-bus` and `pilates` all tie on momentum (4):
`stakes` breaks `pulse` ahead (`product` outranks `personal`), and since
`ha-doukas-bus` and `pilates` tie on `stakes` too, the repo name is what
finally separates them.

## The dashboard

Above the board sits a summary panel — a ring, a total and a split — giving
the whole portfolio's shape before you scroll to a single card. The four stat
tiles it replaces are gone.

### The ring

The ring is steps done over steps total, summed across every tracked
project rather than any one repo's roadmap. It renders only when at least one
card has steps to count; a portfolio with no `steps` anywhere shows no ring.

### The stakes split

Alongside the ring, the week's total commit count, and a segmented bar
showing that total's split across `revenue`, `product` and `personal` — the
same three `stakes` values used for tiebreaking on the board itself. It is a
share of *this week's* commits, not a lifetime figure, and it renders only
once at least one repo has reported one.

### Pace

Every row — the hero included — can carry a pace arrow:

```
pace = commits_7d / (commits_30d / 4.3)
```

`4.3` is the number of weeks in a 30-day window, so the denominator is the
month's weekly average. `↑` appears at a ratio of `1.25` or more, `↓` at
`0.6` or less; between those, or when the month's commit count is unknown,
there is no arrow at all.

Pace goes silent below ten commits in thirty days. Below that floor a single
commit already reads as a 4.3x surge, and a fabricated arrow is worse than a
missing one.

Momentum and pace both come from the same commits call, made against the
repository's **default branch only** — work sitting on an unmerged feature
branch raises neither, even though it may already show up elsewhere as fresh
activity.

### Day and night

The panel follows the device's light or dark setting via
`prefers-color-scheme` — Halo at night, Daylight by day. There is no toggle
and no config option; nothing about the choice is stored.

## Configuration

| Option | Type | Default | Notes |
|---|---|---|---|
| `github_token` | password | — | Fine-grained PAT, Contents: Read-only |
| `repos` | list | — | `owner/repo`, one per line |
| `poll_minutes` | int | `15` | How often the backend hits GitHub |
| `stale_days` | int | `14` | Age at which a project is considered rotted |

Example:

```yaml
github_token: github_pat_xxxxxxxxxxxx
repos:
  - DjBac/nostos
  - DjBac/pounta-sunbed-booking
  - Oikovis/pulse
poll_minutes: 15
stale_days: 14
```

## Token scope

Use a **fine-grained** personal access token, not a classic one.

- Repository access: *Only select repositories* — pick exactly the ones listed
- Permissions: **Contents → Read-only**. Nothing else.

That is the entire scope required. If v2 adds write-back, that will need
Contents: Read and write — treat it as a separate decision at the time.

## How a row is coloured

Colour reflects health, which is a separate axis from ordering. Age is measured
from the repo's last push, not from anything you type.

| Condition | State |
|---|---|
| `blocker` non-empty | **blocked** |
| `phase` is `parked` | **parked** |
| no age available | unknown |
| pushed within 6 days | **fresh** |
| pushed 7 to `stale_days` days ago | **aging** |
| pushed longer ago than `stale_days` | **stale** |

Conditions are checked in that order, so a blocked project reads as blocked
even if it was pushed to this morning.

## Keeping it current

The board is only as honest as its headers. The convention that keeps it
current is to update the header as a by-product of finishing work, rather than
as a separate thing to remember:

> Before closing out a working session, update the front-matter block at the
> top of `STATE.md`: mark newly finished steps `[x]`, move the single `[>]` to
> the true current step (or leave none if nothing is in flight), set `blocker`
> if something external is holding this up (empty string otherwise), and
> correct `phase`, `stakes` or `target` if the shape of the project has
> changed. There is no date to maintain and nothing to re-score — freshness
> and ordering both come from your commits, not from anything typed here.

Put that wherever the repo keeps its contributor instructions.

## Troubleshooting

**Add-on won't appear after adding the repository** — the store caches. Three-dot
menu → Check for updates, then hard-reload the page.

**All cards say "Token rejected"** — the PAT is fine-grained but the repositories
weren't individually selected, or Contents permission is missing.

**A card says "No STATE.md in this repo"** — expected until you backfill. It is
shown rather than hidden on purpose, so gaps stay visible.

**Nothing updates** — check the add-on Log tab for a `Refreshed N repos` line.
The panel polls the backend every two minutes and on tab focus; the backend
polls GitHub on `poll_minutes`. Refresh forces a real GitHub pull.

## Rate limits

Non-issue at this scale: 5,000 authenticated requests per hour against three
requests per repo per `poll_minutes` — one for metadata, one for commit
activity, one for `STATE.md`.
