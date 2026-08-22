# Absorption plan — Gnomon as an Argus module

Companion to `docs/ABSORPTION-BRIEF.md`, which describes **what Gnomon is**.
This document describes **how Argus takes it in**: where it lives, what moves
verbatim, what is rewritten, in what order, and what "done" means.

Written 2026-08-22 on Anthony's decision. Gnomon is at 0.5.8, deployed, 188
assertions passing. Source is at `~/Code/gnomon` and readable directly — nothing
in this plan requires it to be copied first.

---

## 1 · What the module is

**Name: `projects`.** It answers one question — *what should I work on now* —
and it is the only module in Argus whose subject is Anthony's work rather than
his infrastructure.

It follows the shape Argus already uses for `compute` and `storage`: a collector
gathers facts, a module turns them into judgments server-side, and a view
renders what it is given and judges nothing.

**Boundaries.** The module owns: the `STATE.md` contract, ranking, and every
judgment derived from it. It does **not** own: rendering, the component
landscape, or design conformance — those are Argus's, per the ownership seam in
`docs/superpowers/specs/2026-08-22-projects-view-design.md` §12.

**What it must never do.** Write to any repository. Gnomon is read-only by
design and v2 write-back was deferred deliberately. Absorption does not change
that; the only writes are Argus's own store.

---

## 2 · Where each piece lands

| From Gnomon | To Argus | How |
|---|---|---|
| `gnomon/ranking.py` (473 lines) | `backend/argus/projects/ranking.py` | **Verbatim.** stdlib only |
| `gnomon/state.py` (169) | `backend/argus/projects/state.py` | **Verbatim.** `yaml` + stdlib |
| `gnomon/github.py` (87) | `backend/argus/collectors/projects.py` | **Rewritten, not lifted.** It imports `aiohttp`; Argus is an `httpx` codebase throughout. The four calls, their parameters and their error notes survive as a specification — the transport does not. Most of its 73 code lines are shape rather than logic |
| `gnomon/app.py` (405) | `backend/argus/projects/assemble.py` | **Card assembly only.** Options, routes and `/data` persistence are discarded — Argus has all three |
| `gnomon/selftest.py` (1123) | `backend/tests/test_projects_*.py` | **Assertions port, harness does not.** 188 plain-function assertions become pytest |
| `gnomon/www/index.html` (1288) | `frontend/src/views/Projects/` | **Discarded and rebuilt** from Argus components |
| — | `frontend/src/components/Verdict/` | **New.** Argus's to design; see the spec |
| `gnomon/config.yaml` | `config/profiles/*.yaml` | Repo list, `stale_days`, interval become profile config |
| `gnomon/DOCS.md`, `CHANGELOG.md` | — | Historical. Stay in the archived repo |

**A package, not two loose files.** `ranking.py` and `state.py` arrive as a pair
with a shared contract and should live under `backend/argus/projects/` rather
than flat beside `compute.py`, because they carry their own tests and their own
invariants.

**Why the two big ones move verbatim.** They have a standing rule never to
import `aiohttp` — written so the suite could run outside the container. The
consequence is no I/O, no framework and no network in either file. Changing them
during the move would forfeit the 188 assertions that currently prove them, so
the move should be a copy, and any cleanup a separate commit afterwards.

---

## 3 · The collector

`plugin_id: "projects"`. Registered like every other plugin, enabled only via a
profile, never imported by core.

**Four calls per repository per cycle**, all already written in `github.py`:
repo metadata, `STATE.md` contents, commits since 30 days, and commits filtered
to `path=STATE.md`. About 192 calls an hour for 12 repositories against a
5,000/hour limit.

**Failure isolation is already the behaviour, not a new requirement.** A failed
activity call returns `(None, note)` and never an empty list, because an
unreachable API must not make an active project look dormant. The runner's
bulkheads and this contract agree; do not "simplify" the `None` away.

**The requirement most likely to be lost in translation:** the fourth call
exists to subtract status commits. `pushed_at` is repo-level, so a one-line
`STATE.md` edit made every dormant project report as freshly worked — *feeding
the board corrupted the board*. Subtract the `path=STATE.md` SHAs from the
commit list before counting anything. This is stated in the brief's invariants
and belongs in the collector's docstring.

**New outputs Gnomon never produced**, needed by the view: per-project weekly
buckets published as a metric `series`, and step completions recorded as events
so steps-per-week becomes measurable.

---

## 4 · Configuration and secrets

| Item | Today | In Argus |
|---|---|---|
| GitHub PAT | HA add-on option `github_token` | `.env` beside `HA_TOKEN` and the rest |
| Repository list | Add-on option, 12 entries | Profile YAML |
| `stale_days` | 14 | Profile YAML |
| Poll interval | 15 min | Runner schedule |

**A known limitation that survives the move:** the PAT is fine-grained and
therefore single-owner. `Oikovis/pulse` is public but returns 404 because the
token is scoped to `DjBac`. One token cannot read it. Not a bug to fix during
absorption — a constraint to carry, and to state in the profile comments so the
next person does not spend an afternoon on it.

---

## 5 · Data continuity

The only persistent state Gnomon holds is `/data/gnomon-seen.json` — what each
repository's `phase`, `stakes` and `target` were on the previous poll, so that a
field disappearing can be reported.

**Recommendation: do not migrate it.** Let the first poll after cutover
establish a fresh baseline. The entire cost is that a field removed during the
migration window goes unreported once. The memory is not precious and a
migration script for it would be more code than the feature.

`/data/gnomon-theme.json` dies with the panel.

---

## 6 · Order of operations

Each phase is independently shippable and has a gate. **The add-on keeps running
untouched until phase 4.**

**Phase 0 — decided, not pending.** Anthony ruled: *"confirming the absorption,
gnomon first, then the argus tokens then the next task."* Recorded in Argus's
`ROADMAP.md` at `173c99e`, ahead of the numbered programme with the existing
numbers deliberately unchanged. The concern that Projects would be built on
patterns already agreed to be wrong was raised and overruled on timing.

**The mitigation is binding on phase 2:** Projects is built to the *agreed*
pattern, not the current one — status renders as a dot **plus a word**, every
value references a token, and `Register.module.css` is not imported for page
chrome. Built that way, Projects is not the fifth place to fix; it is the
reference the later retrofit aims at.

**Phase 1 — the module, headless.** Copy `ranking.py` and `state.py`, port the
assertions, write the collector. No UI. **Gate:** the collector produces correct
card data for all 12 repositories, and the ported assertions pass.

**Phase 2 — the view.** `views/Projects/` plus `components/Verdict/`, verdict in
all three forms, ranked list, attention band, Overview line. **Gate:** the board
in Argus and the board in Home Assistant agree on ordering, hero and rescue for
a full week.

**Phase 3 — what history unlocks.** Forecast, slip history, blocked-for, stakes
drift, focus, since-you-were-away. Each abstains until it can compute, so they
can ship early and light up on their own. **Gate:** none needed — additive.

**Phase 4 — retirement.** Remove the add-on, the sidebar entry, and the add-on
repository from Home Assistant. Archive `~/Code/gnomon`.

---

## 7 · Retirement criteria

Do not begin phase 4 until all four hold:

1. The Projects view has been live for **two weeks**.
2. Both boards have agreed on ordering, hero and rescue throughout.
3. At least one push has fired correctly, or Anthony has explicitly waived it.
4. **Anthony says so.** Not inferred from the other three.

**Rollback:** keep the add-on installed but stopped for four weeks after
retirement. Restarting it is a single Supervisor action and it needs no state
that Argus will have taken.

---

## 8 · What Argus inherits permanently

**The `STATE.md` contract.** Every tracked repository carries the six-field
front-matter header, and Argus's own `STATE.md` is one of them — after
absorption Argus reads its own status file. The schema is in the brief §2 and
does not change. Any repository Anthony creates from now on gets that header and
appears on the board automatically; that pull-not-push property is the reason
the system has never needed maintaining.

**The invariants**, mapped to Argus's existing mechanisms rather than ported as
a parallel set — see the spec §5A. Three of the four already have twins in
Argus, arrived at independently.

**The archived repository stays readable.** `~/Code/gnomon` holds eight releases
of reasoning in `CHANGELOG.md`, `docs/known-issues.md` and `docs/HANDOFF.md`,
including the defects deliberately not fixed. Archive it; do not delete it.
Several decisions that look arbitrary in the ported code are explained only
there.
