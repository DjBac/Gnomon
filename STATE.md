---
project: Gnomon
phase: usable
stakes: personal
target: ""
blocker: ""
steps:
  - "[x] Six-field header with computed priority"
  - "[x] Freshness derived from the repo's last push"
  - "[x] Published as a Home Assistant add-on repository"
  - "[x] Get the add-on running in Home Assistant"
  - "[x] Backfill STATE.md headers across remaining repos"
  - "[x] Panel redesign for the six-field card"
  - "[x] Momentum board with hero and rescue"
  - "[x] Activity dashboard with day and night themes"
  - "[x] Explain momentum rank in order_reason, not just the count"
---

# Gnomon

Read-only project status board, shipped as a Home Assistant add-on
from the `gnomon` repository.

## Decided
- Schema: 6 fields — `project`, `phase`, `stakes`, `target`, `blocker`, `steps`.
  `updated` is derived from the repo's last push; ordering is computed from
  deadline and momentum on every poll, never stored.
- Source of truth: `STATE.md` front-matter per repo. Pull, not push.
- Surface: HA add-on, ingress panel, sidebar entry.
- Distribution: add-on repository, not a local `/addons` folder.
- Read-only v1; write-back deferred to v2.

## Open

Read `docs/HANDOFF.md` first. Parked technical findings are in
`docs/known-issues.md`.

**Next — undecided.** The momentum-tier fix is done: `ranking.order_reason`
now returns `"momentum 154 - 18 this week, 100 this month"` for the momentum
tier, naming the sort key and both its inputs. The collapsed row still shows
`18/wk`; the arithmetic lives one tap away in the expanded view. Released as
0.5.1.

The strongest remaining candidate is the `--unknown-c` routing in
`docs/known-issues.md`: it reaches `.seg.done` through `--accent`, so an
unknown-state card reads 0% progress regardless. It is a panel change, so it
needs a DOM stub harness.

- `Oikovis/pulse` is unreachable. Fine-grained PATs are scoped to a single
  resource owner, so a `DjBac` token cannot read it even though it is public,
  and GitHub returns 404 rather than 403. The add-on takes one `github_token`.
  Deferred by Anthony 2026-08-22.
- `portolan` is configured but local only — `~/Code/portolan` is not a git repo
  and has no `STATE.md`. Its card is correct until it is pushed.
- `--unknown-c` reaches `.seg.done` via `--accent`, so an unknown card's
  progress reads 0% regardless. Fix by narrowing which consumers take it, not by
  changing the tone.
- The rescue slot stays idle until roughly 2026-09-01. Seeding headers into ten
  repos on 2026-08-17 reset every `pushed_at`, so no repo can cross the stale
  threshold before then. Expected, not broken.
- Nothing has been verified in a real browser. localhost is blocked in the
  agent environment; Anthony is the only one who can look at the panel.
