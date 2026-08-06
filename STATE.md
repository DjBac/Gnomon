---
project: Gnomon
next: "Backfill STATE.md headers across remaining repos"
blocker: ""
updated: 2026-08-06
---

# Gnomon

Read-only project status board, shipped as a Home Assistant add-on
from the `gnomon` repository.

## Decided
- Schema: 4 fields — `project`, `next`, `blocker`, `updated`. No phase, no stakes.
- Source of truth: `STATE.md` front-matter per repo. Pull, not push.
- Surface: HA add-on, ingress panel, sidebar entry.
- Distribution: add-on repository, not a local `/addons` folder.
- Read-only v1; write-back deferred to v2.

## Open
- Session-end header convention rolled out across all repos
- Backfill headers repo by repo
