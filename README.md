> # ◈ DECOMMISSIONED
>
> **This repository is closed. Gnomon now lives inside Argus.**
>
> Anthony decided on 2026-08-22 that Argus absorbs Gnomon entirely. Everything
> needed to build, understand or maintain it is in `~/Code/argus`:
>
> | What | Where |
> |---|---|
> | What Gnomon is, the rules, the invariants | `argus/docs/gnomon/ABSORPTION-BRIEF.md` |
> | How Argus takes it in, as a module | `argus/docs/gnomon/ABSORPTION-PLAN.md` |
> | The Projects view design | `argus/docs/gnomon/PROJECTS-VIEW-DESIGN.md` |
> | The panel's own handoff, for history | `argus/docs/gnomon/GNOMON-HANDOFF.md` |
> | Deferred defects | `argus/docs/gnomon/KNOWN-ISSUES.md` |
> | Eight releases of reasoning | `argus/docs/gnomon/GNOMON-CHANGELOG.md` |
> | `ranking.py`, `state.py`, `github.py`, `selftest.py` | `argus/docs/gnomon/source/` |
>
> **Do not develop here.** Fixes, features and design decisions belong in Argus.
> This repository stays readable because several decisions look arbitrary in the
> ported code and are explained only in its history.
>
> The Home Assistant add-on may still be running. It is unsupported from this
> point and is removed once the Argus Projects view is trusted.

# Venitis Add-ons

Home Assistant add-on repository.

## Installation

Settings → Add-ons → Add-on Store → ⋮ → **Repositories**, then add:

```
https://github.com/DjBac/Gnomon
```

## Add-ons

### [Gnomon](./gnomon)

At-a-glance project status board. Reads a six-field header — including a
`steps` list — from each of your GitHub repos' `STATE.md` and renders one
line per project in the HA sidebar. Cards are ordered by imminent deadline
first, then by momentum from recent commit activity.

See [the docs](./gnomon/DOCS.md) for configuration and token scope.
