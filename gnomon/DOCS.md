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
next: "Wire Stripe webhook to delivery unlock"
blocker: ""
updated: 2026-08-06
---
```

Everything below the closing `---` is freeform — notes, decisions, scratch. The
header is the only part anything depends on.

Four fields, no more. `phase` and `stakes` were considered and cut. Add them
only if their absence actually costs you something.

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

| Condition | State | Effect |
|---|---|---|
| `blocker` non-empty | **blocked** | red rule, sorted to top |
| `updated` older than `stale_days` | **stale** | dimmed, sorted high |
| `updated` 7 to `stale_days` days old | **aging** | amber |
| `updated` within 6 days | **fresh** | green, sorted last |
| missing or unparseable `updated` | unknown | dimmed |

Problems sort to the top. The bottom of the list is the healthy part — if you
never scroll that far, nothing is wrong.

## Keeping it current

The board is only as honest as its headers. The convention that keeps it
current is to update the header as a by-product of finishing work, rather than
as a separate thing to remember:

> Before closing out a working session, update the front-matter block at the
> top of `STATE.md`: set `next` to the single most useful next action, set
> `blocker` if something external is holding this up (empty string otherwise),
> and set `updated` to today's date.

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

Non-issue at this scale: 5,000 authenticated requests per hour against roughly
one request per repo per `poll_minutes`.
