---
project: Gnomon
phase: parked
stakes: personal
target: ""
blocker: ""
steps:
  - "[x] Six-field header with computed priority"
  - "[x] Freshness derived from the last real code commit"
  - "[x] Published as a Home Assistant add-on repository"
  - "[x] Get the add-on running in Home Assistant"
  - "[x] Backfill STATE.md headers across remaining repos"
  - "[x] Panel redesign for the six-field card"
  - "[x] Momentum board with hero and rescue"
  - "[x] Activity dashboard with day and night themes"
  - "[x] Explain momentum rank in order_reason, not just the count"
  - "[x] Freshness ignores status-only commits"
  - "[x] Rescue keys on stalled work, not on age"
  - "[x] One now panel replaces the summary and the hero"
  - "[x] A deadline leads only when it is at risk"
  - "[x] Four-week activity panel that reads itself"
  - "[x] Theme switch and version footprint"
  - "[x] Absorbed into Argus; this repository is closed"
---

# Gnomon

Read-only project status board, shipped as a Home Assistant add-on
from the `gnomon` repository.

## Decided
- Schema: 6 fields — `project`, `phase`, `stakes`, `target`, `blocker`, `steps`.
  `updated` is the repo's last push; freshness and momentum come from commits
  that touched something other than STATE.md, so maintaining the board does not
  make a project look worked on. Ordering is computed on every poll, never
  stored.
- Source of truth: `STATE.md` front-matter per repo. Pull, not push.
- Surface: HA add-on, ingress panel, sidebar entry.
- Distribution: add-on repository, not a local `/addons` folder.
- Read-only v1; write-back deferred to v2. The one exception is the theme
  choice, stored in `/data` from 0.5.8 — a display preference, not project
  state, and it keeps `localStorage` barred.

## Open

**Nothing. This repository is decommissioned.** Argus absorbs Gnomon entirely —
the board becomes a Projects view there, fed by a collector. Everything needed
to continue the work is under `~/Code/argus/docs/gnomon/`, including the four
Python modules and eight releases of reasoning.

Open threads moved with it: the `--unknown-c` routing, the sub-AA text tiers,
and the carried defects are all in `KNOWN-ISSUES.md` there. Two configuration
limits survive the move and are stated in the brief — `Oikovis/pulse` is
unreachable because fine-grained PATs are single-owner, and `portolan` is local
only.

- `Oikovis/pulse` is unreachable. Fine-grained PATs are scoped to a single
  resource owner, so a `DjBac` token cannot read it even though it is public,
  and GitHub returns 404 rather than 403. The add-on takes one `github_token`.
  Deferred by Anthony 2026-08-22.
- `portolan` is configured but local only — `~/Code/portolan` is not a git repo
  and has no `STATE.md`. Its card is correct until it is pushed.
- `--unknown-c` reaches `.seg.done` via `--accent`, so an unknown card's
  progress reads 0% regardless. Fix by narrowing which consumers take it, not by
  changing the tone.
- The rescue slot now keys on stall, not debt, so it stays silent until a
  project genuinely dies mid-flight. Seasonal projects may pass through it
  briefly while their last real commits age out of the 30-day window; that
  self-corrects. Only `phase: parked` can tell "stopped for summer" from
  "stopped by accident", and Anthony chose to leave those repos unparked.
- Nothing has been verified in a real browser. localhost is blocked in the
  agent environment; Anthony is the only one who can look at the panel.
