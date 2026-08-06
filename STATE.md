---
project: Gnomon
phase: usable
stakes: personal
target:
next: "Backfill STATE.md headers across remaining repos"
blocker: ""
---

# Gnomon

Read-only project status board, shipped as a Home Assistant add-on
from the `gnomon` repository.

## Decided
- Schema: 6 fields — `project`, `phase`, `stakes`, `target`, `next`, `blocker`.
  `updated` is derived from the repo's last push; `priority` is computed, never stored.
- Source of truth: `STATE.md` front-matter per repo. Pull, not push.
- Surface: HA add-on, ingress panel, sidebar entry.
- Distribution: add-on repository, not a local `/addons` folder.
- Read-only v1; write-back deferred to v2.

## Open
- Session-end header convention rolled out across all repos
- Backfill headers repo by repo
