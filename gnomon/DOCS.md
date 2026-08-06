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
next: "Wire Stripe webhook to delivery unlock"
blocker: ""
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
| `next` | free text, may be empty | empty |
| `blocker` | free text, empty means not blocked | empty |

Unknown keys are ignored rather than rejected, so a repo can carry extra header
fields for its own purposes. Malformed YAML is caught and surfaced as a note on
the card — it never takes the board down.

### Two fields that are deliberately absent

`updated` used to be a field. It is now derived from the repo's `pushed_at`
timestamp via the GitHub API. A hand-maintained freshness date is the one field
guaranteed to be wrong exactly when it matters, because the moment you stop
touching a project is also the moment you stop updating its header.

`priority` is never stored. It is computed on every poll from `stakes`,
`target`, `blocker` and `phase` — see below. A stored priority is a judgment
frozen at the time of writing; a computed one moves on its own as a deadline
approaches.

The rule behind both: facts come from the GitHub API, judgments come from
`STATE.md`. Anything derivable is derived.

## How priority is computed

A base weight from `stakes`, multiplied by an urgency factor from `target`:

| `stakes` | Base |
|---|---|
| `revenue` | 4.0 |
| `product` | 2.0 |
| `personal` | 1.0 |

| Days to `target` | Urgency |
|---|---|
| no target | 1.0 |
| over 180 | 1.0 |
| 91 to 180 | 1.3 |
| 31 to 90 | 1.7 |
| 0 to 30 | 2.4 |
| overdue | 3.0 |

```
score = base × urgency
if blocker is non-empty:  score × 1.4
if phase == parked:       score × 0.2
```

Rounded to two decimals. The score then lands in a band:

| Score | Band |
|---|---|
| 4.0 and above | high |
| 2.0 to 3.99 | normal |
| below 2.0 | low |

Worked examples:

| Stakes | Target | Blocked | Phase | Score | Band |
|---|---|---|---|---|---|
| revenue | +420d | no | building | 4.0 | high |
| revenue | +20d | no | building | 9.6 | high |
| revenue | overdue 5d | no | shipped | 12.0 | high |
| product | none | no | shipped | 2.0 | normal |
| product | none | no | parked | 0.4 | low |
| personal | none | no | usable | 1.0 | low |
| personal | none | yes | shipped | 1.4 | low |

The board sorts by score descending, then by age descending. Blocked work is
not special-cased to the top — the 1.4× multiplier means it rises on its own
merits, and a blocked personal side project stays below unblocked revenue work,
which is usually the honest ordering.

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

Colour reflects health, which is a separate axis from priority. Age is measured
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
> top of `STATE.md`: set `next` to the single most useful next action, set
> `blocker` if something external is holding this up (empty string otherwise),
> and correct `phase`, `stakes` or `target` if the shape of the project has
> changed. There is no date to maintain — freshness comes from the last push.

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

Non-issue at this scale: 5,000 authenticated requests per hour against two
requests per repo per `poll_minutes` — one for metadata, one for `STATE.md`.
