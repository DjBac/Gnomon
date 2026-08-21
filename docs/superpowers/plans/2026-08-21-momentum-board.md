# Momentum Board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Gnomon's degenerate `stakes × target` ordering with a momentum-driven board — one hero card, one optional rescue slot, a calm tail — using signals derived from commit activity rather than hand-maintained fields.

**Architecture:** `app.py` splits into four focused modules. `state.py` and `ranking.py` are pure (no network, no `aiohttp`), so `selftest.py` runs under plain `python3`. `github.py` is thin IO. `app.py` assembles cards and serves HTTP. Ordering is two-tier — imminent deadlines first, then momentum — with a separate debt signal that marks cards and picks the rescue slot but never affects position.

**Tech Stack:** Python 3.12, `aiohttp` 3.9.5, `PyYAML` 6.0.1. Vanilla HTML/CSS/JS, single file, no build step. Home Assistant add-on on Alpine.

**Spec:** `docs/superpowers/specs/2026-08-21-momentum-board-design.md`

## Global Constraints

- **No new dependencies.** `aiohttp` and `PyYAML` only. No test framework — tests are a dependency-free `selftest.py`.
- **No attribution of any kind** in code, comments, docs or commit messages. Commit messages describe the change only.
- **Never commit or push without explicit permission.** Each task ends with a local commit; pushing is a separate decision by Anthony.
- **`state.py` and `ranking.py` MUST NOT import `aiohttp`.** This is what keeps tests runnable outside the container. Enforced by a test in Task 1.
- **Relative fetch paths only** in `index.html` — a leading `/` breaks HA ingress.
- **No `localStorage`, no `sessionStorage`, no external fonts, CDNs or scripts** in `index.html`.
- **Build the panel's DOM with `createElement` / `textContent`.** Never assign `innerHTML`, and never concatenate HTML strings. Enforced by a check in Task 6.
- **Do not modify** `build.yaml`, `run.sh`, `repository.yaml`, `README.md`, `.gitignore`, `icon.png`, `logo.png`. The **Dockerfile is modified exactly once**, in Task 1.
- **Zero migration.** No `STATE.md` in any repo may need editing.
- Python: 4-space indent, type hints on signatures, minimal comments — only where non-obvious.

---

## File Structure

| File | Responsibility | Imports |
|---|---|---|
| `gnomon/state.py` | Parse `STATE.md`: front-matter, steps, dates, field normalisation, vanished-field diffing | `yaml`, stdlib |
| `gnomon/ranking.py` | Momentum, debt, ordering, roles, human reasons | stdlib only |
| `gnomon/github.py` | The three API calls and their error notes | `aiohttp`, stdlib |
| `gnomon/app.py` | Options, card assembly, seen-state persistence, HTTP routes, startup | all of the above |
| `gnomon/selftest.py` | All tests. Imports `state` + `ranking` only | stdlib |
| `gnomon/www/index.html` | Hero / rescue / tail panel | none |
| `gnomon/Dockerfile` | `COPY *.py /app/` instead of `COPY app.py` | — |

---

## Task 1: Split `app.py` into modules

Pure refactor. **No behaviour changes.** The gate is that existing tests still pass *and* now run without `aiohttp` installed.

**Files:**
- Create: `gnomon/state.py`, `gnomon/ranking.py`, `gnomon/github.py`, `gnomon/selftest.py`
- Modify: `gnomon/app.py`, `gnomon/Dockerfile`

**Interfaces:**
- Consumes: nothing.
- Produces: the module layout every later task builds on. Exact moves listed below.

- [ ] **Step 1: Create `gnomon/state.py`**

Move these from `app.py` **unchanged** (current line numbers in parentheses):
`parse_front_matter` (82), `to_date` (99), `today_utc` (113), `days_since` (117), `days_until` (125), `normalise_phase` (133), `normalise_stakes` (139), `parse_steps` (145), `current_step` (183).

Move these constants: `PHASES` (50), `STEP_PREFIXES` (53), `DEFAULT_STAKES` (55).

`normalise_stakes` currently reads `STAKES_BASE.keys()`, which is moving to `ranking.py`. Break that dependency by adding a local tuple and using it:

```python
STAKES = ("revenue", "product", "personal")


def normalise_stakes(value) -> str:
    """A recognised stakes level, defaulting to personal."""
    stakes = str(value or "").strip().lower()
    return stakes if stakes in STAKES else DEFAULT_STAKES
```

File header:

```python
"""Reading STATE.md into typed values. No network, no aiohttp."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

import yaml

LOG = logging.getLogger("gnomon")
```

- [ ] **Step 2: Verify `state.py` imports without aiohttp**

Run: `cd gnomon && python3 -c "import state; print(state.PHASES)"`
Expected: `['idea', 'building', 'usable', 'shipped', 'parked']`

- [ ] **Step 3: Create `gnomon/ranking.py`**

Move from `app.py` unchanged: `urgency` (190), `target_phrase` (205), `score_factors` (223), `compute_score` (246), `band` (256), `classify` (264), `sort_cards` (408). Move constants `STAKES_BASE` (54), `BLOCKED_MULTIPLIER` (57), `PARKED_MULTIPLIER` (58), `FRESH_MAX` (48).

Most of this is deleted in Task 3 — moving it now keeps Task 1 a genuine no-op refactor with a clean gate.

```python
"""Ordering: how cards are ranked and why. No network, no aiohttp."""

from __future__ import annotations

FRESH_MAX = 6
STAKES_BASE = {"revenue": 4.0, "product": 2.0, "personal": 1.0}
DEFAULT_STAKES = "personal"
BLOCKED_MULTIPLIER = 1.4
PARKED_MULTIPLIER = 0.2
```

- [ ] **Step 4: Create `gnomon/github.py`**

Move from `app.py` unchanged: `meta_note` (301), `fetch_pushed_at` (311), `fetch_state_md` (328). Move constant `GITHUB_API` (44).

```python
"""GitHub API calls. The only module that touches the network."""

from __future__ import annotations

import asyncio
import json

import aiohttp

GITHUB_API = "https://api.github.com"
```

- [ ] **Step 5: Create `gnomon/selftest.py`**

Move `selftest` (491) and `selftest_steps` (531) from `app.py`. Replace their bare references with module-qualified ones — `compute_score` becomes `ranking.compute_score`, `parse_steps` becomes `state.parse_steps`, and so on.

```python
"""Dependency-free tests. Run: python3 gnomon/selftest.py"""

from __future__ import annotations

import sys

import ranking
import state


def main() -> int:
    failures = 0
    failures += selftest_priority()
    failures += selftest_steps()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Rename `selftest` to `selftest_priority` for clarity. Each `selftest_*` returns `0` on success and `1` on failure.

- [ ] **Step 6: Rewrite `app.py` to import the modules**

Delete every moved function. Keep `load_options`, `new_card`, `fetch_repo`, `refresh`, `poll_loop`, the four handlers, `on_startup`, `on_cleanup`, `main`. Delete the `--selftest` branch at the bottom — `selftest.py` is the entry point now.

```python
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
from aiohttp import web

import github
import ranking
import state
```

Qualify every moved call. For example in `fetch_repo`:

```python
    steps, steps_note = state.parse_steps(meta.get("steps"))
    card["state"] = ranking.classify(
        card["blocker"], card["phase"], card["age"], stale_days
    )
```

- [ ] **Step 7: Run the tests**

Run: `python3 gnomon/selftest.py`
Expected: the 7 priority cases pass, `factors reconcile with score: yes`, the 8 step-parser cases pass, exit code 0.

This is the key gate: it runs on a machine with no `aiohttp` installed.

- [ ] **Step 8: Add a test that enforces the dependency boundary**

In `selftest.py`, before `main`:

```python
def selftest_no_network_deps() -> int:
    """state and ranking must stay importable without aiohttp."""
    here = pathlib.Path(__file__).parent
    bad = []
    for name in ("state", "ranking"):
        source = (here / f"{name}.py").read_text(encoding="utf-8")
        if "import aiohttp" in source or "from aiohttp" in source:
            bad.append(name)
    print(f"{'FAIL' if bad else 'PASS'}  pure modules free of aiohttp"
          f"{': ' + ', '.join(bad) if bad else ''}")
    return 1 if bad else 0
```

Call it first in `main()`. Add `import pathlib` at the top of `selftest.py`. Reading via `__file__` means the test works from any working directory.

The check looks for an actual import statement, not the bare word — the module docstrings above legitimately mention aiohttp in prose.

- [ ] **Step 9: Run the tests again**

Run: `python3 gnomon/selftest.py`
Expected: `PASS  pure modules free of aiohttp`, then all previous tests pass, exit 0.

- [ ] **Step 10: Verify the app still starts**

Run: `cd gnomon && python3 -c "import ast,sys; [ast.parse(open(f).read()) for f in ('app.py','state.py','ranking.py','github.py','selftest.py')]; print('all parse')"`
Expected: `all parse`

- [ ] **Step 11: Update the Dockerfile**

Modify `gnomon/Dockerfile`, replacing the single COPY line:

```dockerfile
COPY *.py /app/
COPY www /app/www
COPY run.sh /run.sh
```

`run.sh` still runs `python3 /app/app.py`, and `WORKDIR /app` means sibling imports resolve. No change to `run.sh`.

- [ ] **Step 12: Commit**

```bash
git add gnomon/state.py gnomon/ranking.py gnomon/github.py gnomon/selftest.py gnomon/app.py gnomon/Dockerfile
git commit -m "Split the backend into focused modules"
```

---

## Task 2: Fetch commit activity

**Files:**
- Modify: `gnomon/github.py`
- Modify: `gnomon/ranking.py`
- Modify: `gnomon/selftest.py`

**Interfaces:**
- Consumes: `github.meta_note(status) -> str` from Task 1.
- Produces:
  - `github.fetch_commits(session, repo, since) -> tuple[list | None, str]` — raw commit payload or `None`, plus a note. `since` is the ISO timestamp from `ranking.commit_cutoffs`.
  - `ranking.count_commits(payload, cut7) -> tuple[int, int]` — `(commits_7d, commits_30d)`.
  - `ranking.commit_cutoffs(now) -> tuple[str, str]` — `(since_iso, cut7_date)`.

- [ ] **Step 1: Write the failing tests**

Add to `gnomon/selftest.py`:

```python
def selftest_commits() -> int:
    """Counting commits out of an API payload."""
    def c(day):
        return {"commit": {"committer": {"date": f"{day}T10:00:00Z"}}}

    cases = [
        ("all recent", [c("2026-08-20"), c("2026-08-19")], "2026-08-14", (2, 2)),
        ("split window", [c("2026-08-20"), c("2026-08-01")], "2026-08-14", (1, 2)),
        ("none recent", [c("2026-08-01"), c("2026-07-25")], "2026-08-14", (0, 2)),
        ("empty", [], "2026-08-14", (0, 0)),
        ("malformed entry", [c("2026-08-20"), {"nope": 1}], "2026-08-14", (1, 2)),
        ("boundary is inclusive", [c("2026-08-14")], "2026-08-14", (1, 1)),
    ]
    failures = 0
    for label, payload, cut7, want in cases:
        got = ranking.count_commits(payload, cut7)
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  commits: {label:24} {got}"
              f"{'' if ok else f'  (want {want})'}")

    since, cut7 = ranking.commit_cutoffs(
        datetime.datetime(2026, 8, 21, 12, 0, tzinfo=datetime.timezone.utc)
    )
    ok = since.startswith("2026-07-22") and cut7 == "2026-08-14"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  commits: cutoffs               {since} / {cut7}")
    return 1 if failures else 0
```

Add `import datetime` at the top of `selftest.py` and call `selftest_commits()` from `main()`.

- [ ] **Step 2: Run to verify it fails**

Run: `python3 gnomon/selftest.py`
Expected: FAIL with `AttributeError: module 'ranking' has no attribute 'count_commits'`

- [ ] **Step 3: Implement the counters in `ranking.py`**

```python
import datetime

MOMENTUM_RECENT_DAYS = 7
MOMENTUM_WINDOW_DAYS = 30
RECENT_WEIGHT = 3


def commit_cutoffs(now: datetime.datetime) -> tuple[str, str]:
    """(since timestamp for the API, date string for the 7-day boundary)."""
    since = (now - datetime.timedelta(days=MOMENTUM_WINDOW_DAYS)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    cut7 = (now - datetime.timedelta(days=MOMENTUM_RECENT_DAYS)).date().isoformat()
    return since, cut7


def _commit_day(commit) -> str:
    try:
        return commit["commit"]["committer"]["date"][:10]
    except (KeyError, TypeError, IndexError):
        return ""


def count_commits(payload: list, cut7: str) -> tuple[int, int]:
    """(commits in the recent window, commits in the whole window)."""
    total = len(payload)
    recent = sum(1 for c in payload if _commit_day(c) >= cut7)
    return recent, total
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 gnomon/selftest.py`
Expected: all six commit cases PASS plus the cutoffs case.

- [ ] **Step 5: Add the fetch to `github.py`**

```python
from datetime import datetime, timezone


async def fetch_commits(
    session: aiohttp.ClientSession, repo: str, since: str
) -> tuple[list | None, str]:
    """Commits since a timestamp. Returns (payload, note).

    A failure returns (None, note) and NEVER an empty list — an unreachable
    API must not make an active project look dormant.
    """
    url = f"{GITHUB_API}/repos/{repo}/commits"
    params = {"since": since, "per_page": "100"}
    try:
        async with session.get(
            url, params=params, headers={"Accept": "application/vnd.github+json"}
        ) as response:
            if response.status == 409:
                return [], ""          # empty repository, legitimately quiet
            if response.status != 200:
                return None, "Activity unavailable"
            data = await response.json()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return None, "Activity unavailable"
    except (json.JSONDecodeError, ValueError):
        return None, "Activity unavailable"
    if not isinstance(data, list):
        return None, "Activity unavailable"
    return data, ""
```

- [ ] **Step 6: Verify it parses**

Run: `cd gnomon && python3 -c "import ast; ast.parse(open('github.py').read()); print('ok')"`
Expected: `ok`

- [ ] **Step 7: Commit**

```bash
git add gnomon/github.py gnomon/ranking.py gnomon/selftest.py
git commit -m "Read commit activity from GitHub"
```

---

## Task 3: The ranking engine

**Files:**
- Modify: `gnomon/ranking.py`
- Modify: `gnomon/selftest.py`

**Interfaces:**
- Consumes: `ranking.count_commits`, `ranking.commit_cutoffs` from Task 2.
- Produces:
  - `ranking.momentum(c7, c30) -> int | None`
  - `ranking.debt(age, stale_days, blocker, days_to_target) -> float`
  - `ranking.debt_reason(age, stale_days, blocker, days_to_target) -> str`
  - `ranking.order_key(card) -> tuple`
  - `ranking.order_reason(card) -> tuple[str, str]` — `(long_reason, badge)`
  - `ranking.assign_roles(ordered) -> None` — mutates each card's `role` in place
  - Constants `URGENT_DAYS = 30`, `RESCUE_FLOOR = 1.0`, `RESCUE_MIN_RANK = 5`

Cards passed to these functions are dicts carrying at least: `repo`, `stakes`, `phase`, `blocker`, `next`, `age`, `days_to_target`, `momentum`, `commits_7d`, `commits_30d`, `debt`.

- [ ] **Step 1: Write the failing tests for momentum and debt**

Add to `selftest.py`:

```python
def selftest_momentum() -> int:
    cases = [
        ("very active", 51, 51, 204),
        ("steady", 17, 100, 151),
        ("quiet", 0, 0, 0),
        ("old work only", 0, 12, 12),
        ("unknown stays unknown", None, None, None),
    ]
    failures = 0
    for label, c7, c30, want in cases:
        got = ranking.momentum(c7, c30)
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  momentum: {label:22} {got}"
              f"{'' if ok else f'  (want {want})'}")
    return 1 if failures else 0


def selftest_debt() -> int:
    cases = [
        ("fresh and fine", 2, 14, "", None, 0.14),
        ("one stale period", 14, 14, "", None, 1.0),
        ("blocked", 0, 14, "vendor key", None, 1.5),
        ("overdue", 0, 14, "", -3, 2.0),
        ("everything at once", 28, 14, "vendor key", -3, 5.5),
        ("no age", None, 14, "", None, 0.0),
    ]
    failures = 0
    for label, age, sd, blk, dtt, want in cases:
        got = ranking.debt(age, sd, blk, dtt)
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  debt: {label:26} {got}"
              f"{'' if ok else f'  (want {want})'}")
    return 1 if failures else 0
```

Call both from `main()`.

- [ ] **Step 2: Run to verify they fail**

Run: `python3 gnomon/selftest.py`
Expected: FAIL with `AttributeError: module 'ranking' has no attribute 'momentum'`

- [ ] **Step 3: Implement momentum and debt**

Add to `ranking.py`:

```python
URGENT_DAYS = 30
RESCUE_FLOOR = 1.0
RESCUE_MIN_RANK = 5
BLOCKED_DEBT = 1.5
OVERDUE_DEBT = 2.0
STAKES_ORDER = {"revenue": 0, "product": 1, "personal": 2}


def momentum(c7: int | None, c30: int | None) -> int | None:
    """Weighted commit activity. None means unknown, which is not zero."""
    if c7 is None or c30 is None:
        return None
    return c7 * RECENT_WEIGHT + c30


def debt(
    age: int | None, stale_days: int, blocker: str, days_to_target: int | None
) -> float:
    """How much this project is owed. Marks a card; never moves it."""
    total = 0.0
    if age is not None and stale_days:
        total += age / stale_days
    if blocker:
        total += BLOCKED_DEBT
    if days_to_target is not None and days_to_target < 0:
        total += OVERDUE_DEBT
    return round(total, 2)


def debt_reason(
    age: int | None, stale_days: int, blocker: str, days_to_target: int | None
) -> str:
    """Four words on why this card is owed attention."""
    if blocker:
        return "blocked"
    if days_to_target is not None and days_to_target < 0:
        return f"{-days_to_target}d overdue"
    if age is not None:
        return f"quiet {age} days"
    return ""
```

- [ ] **Step 4: Run to verify they pass**

Run: `python3 gnomon/selftest.py`
Expected: all momentum and debt cases PASS.

- [ ] **Step 5: Write the failing test for ordering and roles**

Add to `selftest.py`:

```python
def _card(repo, **kw):
    base = dict(repo=repo, project=repo, stakes="personal", phase="usable",
                blocker="", next="do a thing", age=3, days_to_target=None,
                momentum=0, commits_7d=0, commits_30d=0, debt=0.0, role="tail")
    base.update(kw)
    return base


def selftest_ordering() -> int:
    failures = 0

    # a near deadline outranks higher momentum
    cards = [_card("busy", momentum=200), _card("due", days_to_target=12, momentum=1)]
    got = [c["repo"] for c in sorted(cards, key=ranking.order_key)]
    ok = got == ["due", "busy"]
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  order: deadline beats momentum  {got}")

    # a distant target does not enter the urgent tier
    cards = [_card("busy", momentum=200), _card("far", days_to_target=400, momentum=1)]
    got = [c["repo"] for c in sorted(cards, key=ranking.order_key)]
    ok = got == ["busy", "far"]
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  order: distant target waits     {got}")

    # two deadlines sort soonest first
    cards = [_card("later", days_to_target=20), _card("sooner", days_to_target=3)]
    got = [c["repo"] for c in sorted(cards, key=ranking.order_key)]
    ok = got == ["sooner", "later"]
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  order: soonest deadline first   {got}")

    # momentum orders the rest, unknown sorts as quiet
    cards = [_card("mid", momentum=50), _card("top", momentum=99),
             _card("unknown", momentum=None), _card("low", momentum=1)]
    got = [c["repo"] for c in sorted(cards, key=ranking.order_key)]
    ok = got == ["top", "mid", "low", "unknown"]
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  order: momentum descending      {got}")

    # stakes breaks a momentum tie
    cards = [_card("personal-one", momentum=5),
             _card("revenue-one", momentum=5, stakes="revenue")]
    got = [c["repo"] for c in sorted(cards, key=ranking.order_key)]
    ok = got == ["revenue-one", "personal-one"]
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  order: stakes breaks the tie    {got}")
    return 1 if failures else 0


def selftest_roles() -> int:
    failures = 0

    def roles(cards):
        ordered = sorted(cards, key=ranking.order_key)
        ranking.assign_roles(ordered)
        return {c["repo"]: c["role"] for c in ordered}

    # hero is the top card
    got = roles([_card("a", momentum=10), _card("b", momentum=1)])
    ok = got["a"] == "hero" and got["b"] == "tail"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  roles: top card is hero         {got}")

    # hero suppressed only when all three are true
    got = roles([_card("empty", momentum=0, next="", days_to_target=None)])
    ok = got["empty"] == "tail"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  roles: quiet board has no hero  {got}")

    # unknown momentum must not suppress the hero
    got = roles([_card("unknown", momentum=None, next="", days_to_target=None)])
    ok = got["unknown"] == "hero"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  roles: unknown keeps the hero   {got}")

    # rescue must come from rank 5 or lower
    pool = [_card(f"r{i}", momentum=100 - i, debt=0.0) for i in range(4)]
    pool.append(_card("rotting", momentum=1, debt=3.0))
    got = roles(pool)
    ok = got["rotting"] == "rescue"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  roles: rescue from below fold   {got.get('rotting')}")

    # a high-debt card already visible is NOT rescued
    pool = [_card("visible", momentum=100, debt=9.0)] + \
           [_card(f"r{i}", momentum=50 - i) for i in range(5)]
    got = roles(pool)
    ok = "rescue" not in got.values()
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  roles: visible debt not rescued {sorted(set(got.values()))}")

    # below the floor, no rescue slot at all
    pool = [_card(f"r{i}", momentum=50 - i, debt=0.5) for i in range(8)]
    got = roles(pool)
    ok = "rescue" not in got.values()
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  roles: floor respected          {sorted(set(got.values()))}")

    # parked is never rescued
    pool = [_card(f"r{i}", momentum=50 - i) for i in range(5)]
    pool.append(_card("parked", momentum=0, debt=9.0, phase="parked"))
    got = roles(pool)
    ok = got["parked"] != "rescue"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  roles: parked never rescued     {got['parked']}")
    return 1 if failures else 0
```

Call both from `main()`.

- [ ] **Step 6: Run to verify they fail**

Run: `python3 gnomon/selftest.py`
Expected: FAIL with `AttributeError: module 'ranking' has no attribute 'order_key'`

- [ ] **Step 7: Implement ordering and roles**

Add to `ranking.py`:

```python
def order_key(card: dict) -> tuple:
    """Deadline tier first, then momentum descending, then stakes."""
    dtt = card.get("days_to_target")
    urgent = dtt is not None and dtt <= URGENT_DAYS
    mom = card.get("momentum")
    return (
        0 if urgent else 1,
        dtt if urgent else 0,
        -(mom if mom is not None else 0),
        STAKES_ORDER.get(card.get("stakes"), 9),
        card.get("repo", ""),
    )


def _hero_is_worth_showing(card: dict) -> bool:
    """A hero needs something to say. Unknown momentum still counts."""
    dtt = card.get("days_to_target")
    if card.get("next"):
        return True
    if dtt is not None and dtt <= URGENT_DAYS:
        return True
    return card.get("momentum") != 0


def assign_roles(ordered: list[dict]) -> None:
    """Set `role` on each card. Mutates in place; `ordered` must be sorted."""
    for card in ordered:
        card["role"] = "tail"
    if not ordered:
        return
    if _hero_is_worth_showing(ordered[0]):
        ordered[0]["role"] = "hero"

    candidates = [
        c
        for c in ordered[RESCUE_MIN_RANK - 1:]
        if c.get("phase") != "parked" and c.get("debt", 0.0) >= RESCUE_FLOOR
    ]
    if candidates:
        max(candidates, key=lambda c: c["debt"])["role"] = "rescue"
```

- [ ] **Step 8: Run to verify they pass**

Run: `python3 gnomon/selftest.py`
Expected: all five ordering cases and all seven role cases PASS.

- [ ] **Step 9: Write the failing test for `order_reason`**

```python
def selftest_order_reason() -> int:
    cases = [
        ("ships soon", _card("a", days_to_target=12),
         ("ships in 12 days", "SHIPS 12d")),
        ("ships today", _card("a", days_to_target=0),
         ("ships today", "SHIPS today")),
        ("overdue", _card("a", days_to_target=-3),
         ("3 days overdue", "3d OVERDUE")),
        ("active", _card("a", commits_7d=51, commits_30d=51, momentum=204),
         ("51 commits this week", "51/wk")),
        ("one commit", _card("a", commits_7d=1, commits_30d=1, momentum=4),
         ("1 commit this week", "1/wk")),
        ("older work only", _card("a", commits_7d=0, commits_30d=9, momentum=9),
         ("9 commits this month", "9/mo")),
        ("quiet", _card("a", commits_7d=0, commits_30d=0, momentum=0, age=94),
         ("quiet for 94 days", "quiet")),
        ("unknown", _card("a", momentum=None, commits_7d=None, commits_30d=None),
         ("activity unknown", "—")),
    ]
    failures = 0
    for label, card, want in cases:
        got = ranking.order_reason(card)
        ok = got == want
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  reason: {label:20} {got}"
              f"{'' if ok else f'  (want {want})'}")
    return 1 if failures else 0
```

Call from `main()`.

- [ ] **Step 10: Run to verify it fails**

Run: `python3 gnomon/selftest.py`
Expected: FAIL with `AttributeError: module 'ranking' has no attribute 'order_reason'`

- [ ] **Step 11: Implement `order_reason`**

```python
def order_reason(card: dict) -> tuple[str, str]:
    """(sentence for the expanded card, badge for the hero)."""
    dtt = card.get("days_to_target")
    if dtt is not None and dtt <= URGENT_DAYS:
        if dtt < 0:
            return f"{-dtt} days overdue", f"{-dtt}d OVERDUE"
        if dtt == 0:
            return "ships today", "SHIPS today"
        return f"ships in {dtt} days", f"SHIPS {dtt}d"

    if card.get("momentum") is None:
        return "activity unknown", "—"

    c7 = card.get("commits_7d") or 0
    c30 = card.get("commits_30d") or 0
    if c7:
        unit = "commit" if c7 == 1 else "commits"
        return f"{c7} {unit} this week", f"{c7}/wk"
    if c30:
        unit = "commit" if c30 == 1 else "commits"
        return f"{c30} {unit} this month", f"{c30}/mo"

    age = card.get("age")
    if age is None:
        return "no activity recorded", "quiet"
    return f"quiet for {age} days", "quiet"
```

- [ ] **Step 12: Run to verify it passes**

Run: `python3 gnomon/selftest.py`
Expected: all eight reason cases PASS.

- [ ] **Step 13: Write the golden-order test**

This locks in the order Anthony approved on 2026-08-21.

```python
GOLDEN = [
    # repo,           stakes,     phase,     dtt,  c7, c30, blocker, age
    ("anthonyvenitis", "revenue",  "usable",   12,   2,  25, "",        4),
    ("argus",          "personal", "usable", None,  51,  51, "",        0),
    ("premiere",       "revenue",  "usable", None,  17, 100, "walk",    4),
    ("nima",           "product",  "building", None, 29, 52, "",        4),
    ("the-bridge",     "product",  "building", None, 22, 22, "queue",   1),
    ("oikovis-autom",  "personal", "usable", None,   2,  15, "",        4),
    ("Gnomon",         "personal", "usable", None,   4,   7, "",        0),
    ("pounta",         "personal", "usable", None,   1,   8, "",        4),
    ("pilates",        "personal", "usable", None,   1,   1, "",        4),
    ("ha-doukas-bus",  "personal", "shipped", None,  1,   1, "",        4),
    ("pulse",          "product",  "building", None, 1,   1, "",        4),
]


def selftest_golden_order() -> int:
    """The eleven real headers must produce the approved order."""
    cards = []
    for repo, stakes, phase, dtt, c7, c30, blocker, age in GOLDEN:
        card = _card(repo, stakes=stakes, phase=phase, days_to_target=dtt,
                     commits_7d=c7, commits_30d=c30, blocker=blocker, age=age)
        card["momentum"] = ranking.momentum(c7, c30)
        card["debt"] = ranking.debt(age, 14, blocker, dtt)
        cards.append(card)
    ordered = sorted(cards, key=ranking.order_key)
    ranking.assign_roles(ordered)
    got = [c["repo"] for c in ordered]
    want = ["anthonyvenitis", "argus", "premiere", "nima", "the-bridge",
            "oikovis-autom", "Gnomon", "pounta", "pulse", "ha-doukas-bus",
            "pilates"]
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  golden order")
    if not ok:
        print(f"    got  {got}")
        print(f"    want {want}")
    hero = [c["repo"] for c in ordered if c["role"] == "hero"]
    hero_ok = hero == ["anthonyvenitis"]
    print(f"{'PASS' if hero_ok else 'FAIL'}  golden hero: {hero}")
    # premiere carries a blocker but sits at rank 3, so it is NOT rescued;
    # the-bridge is the highest-debt card at rank 5 or lower.
    rescue = [c["repo"] for c in ordered if c["role"] == "rescue"]
    rescue_ok = rescue == ["the-bridge"]
    print(f"{'PASS' if rescue_ok else 'FAIL'}  golden rescue: {rescue}")
    return 0 if (ok and hero_ok and rescue_ok) else 1
```

Call from `main()`.

- [ ] **Step 14: Run to verify it passes**

Run: `python3 gnomon/selftest.py`
Expected: `PASS  golden order` and `PASS  golden hero: ['anthonyvenitis']`

If the order differs, the engine is wrong — do not adjust the expectation to match the output.

- [ ] **Step 15: Delete the retired scoring code**

Remove from `ranking.py`: `urgency`, `target_phrase`, `score_factors`, `compute_score`, `band`, `sort_cards`, and constants `STAKES_BASE`, `BLOCKED_MULTIPLIER`, `PARKED_MULTIPLIER`.

Remove `selftest_priority` from `selftest.py` and its call in `main()`.

Keep `classify` and `FRESH_MAX` — colour states are unchanged.

- [ ] **Step 16: Run the tests once more**

Run: `python3 gnomon/selftest.py`
Expected: everything passes; no `NameError` from the deletions. `app.py` still references removed functions and is fixed in Task 5 — that is expected at this point.

- [ ] **Step 17: Commit**

```bash
git add gnomon/ranking.py gnomon/selftest.py
git commit -m "Rank by momentum, with deadlines taking precedence"
```

---

## Task 4: Notice fields that vanish

**Files:**
- Modify: `gnomon/state.py`
- Modify: `gnomon/selftest.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `state.WATCHED_FIELDS` — `("target", "stakes", "phase")`
  - `state.watched_values(meta) -> dict` — the watched subset of a parsed header
  - `state.vanished(previous, current) -> list[str]` — watched keys that had a value and no longer do
  - `state.vanished_note(gone) -> str`

- [ ] **Step 1: Write the failing test**

```python
def selftest_vanished() -> int:
    cases = [
        ("nothing changed",
         {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"},
         {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"}, []),
        ("target removed",
         {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"},
         {"target": "", "stakes": "revenue", "phase": "usable"}, ["target"]),
        ("target changed, not removed",
         {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"},
         {"target": "2028-01-01", "stakes": "revenue", "phase": "usable"}, []),
        ("two removed",
         {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"},
         {"target": "", "stakes": "revenue", "phase": ""}, ["target", "phase"]),
        ("never had one",
         {"target": "", "stakes": "personal", "phase": "usable"},
         {"target": "", "stakes": "personal", "phase": "usable"}, []),
        ("first sighting",
         {}, {"target": "2027-09-30", "stakes": "revenue", "phase": "usable"}, []),
    ]
    failures = 0
    for label, prev, cur, want in cases:
        got = state.vanished(prev, cur)
        ok = sorted(got) == sorted(want)
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  vanished: {label:28} {got}"
              f"{'' if ok else f'  (want {want})'}")
    note = state.vanished_note(["target"])
    ok = note == "target removed since last poll"
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  vanished: note                     {note!r}")
    return 1 if failures else 0
```

Call from `main()`.

- [ ] **Step 2: Run to verify it fails**

Run: `python3 gnomon/selftest.py`
Expected: FAIL with `AttributeError: module 'state' has no attribute 'vanished'`

- [ ] **Step 3: Implement in `state.py`**

```python
WATCHED_FIELDS = ("target", "stakes", "phase")


def watched_values(meta: dict) -> dict:
    """The subset of a header worth remembering between polls."""
    target = to_date(meta.get("target"))
    return {
        "target": target.isoformat() if target else "",
        "stakes": str(meta.get("stakes") or "").strip().lower(),
        "phase": normalise_phase(meta.get("phase")),
    }


def vanished(previous: dict, current: dict) -> list[str]:
    """Watched fields that had a value last time and have none now."""
    if not previous:
        return []
    return [f for f in WATCHED_FIELDS if previous.get(f) and not current.get(f)]


def vanished_note(gone: list[str]) -> str:
    if not gone:
        return ""
    return f"{', '.join(gone)} removed since last poll"
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 gnomon/selftest.py`
Expected: all six vanished cases plus the note case PASS.

- [ ] **Step 5: Commit**

```bash
git add gnomon/state.py gnomon/selftest.py
git commit -m "Notice when a header field disappears"
```

---

## Task 5: Assemble the new card

**Files:**
- Modify: `gnomon/app.py`

**Interfaces:**
- Consumes: everything from Tasks 2–4.
- Produces: the API shape the panel reads in Task 6. Each card carries `repo`, `project`, `phase`, `stakes`, `target`, `days_to_target`, `next`, `steps`, `steps_done`, `steps_total`, `blocker`, `updated`, `age`, `state`, `note`, `commits_7d`, `commits_30d`, `momentum`, `debt`, `debt_reason`, `role`, `order_reason`, `order_badge`. Response envelope unchanged: `projects`, `fetched`, `stale_days`, `phases`, `error`.

- [ ] **Step 1: Update `new_card`**

Replace the `priority`, `score`, `score_factors` entries:

```python
def new_card(repo: str) -> dict:
    return {
        "repo": repo,
        "project": repo.split("/")[-1],
        "phase": "",
        "stakes": state.DEFAULT_STAKES,
        "target": "",
        "days_to_target": None,
        "next": "",
        "steps": [],
        "steps_done": 0,
        "steps_total": 0,
        "blocker": "",
        "updated": None,
        "age": None,
        "state": "unknown",
        "commits_7d": None,
        "commits_30d": None,
        "momentum": None,
        "debt": 0.0,
        "debt_reason": "",
        "role": "tail",
        "order_reason": "",
        "order_badge": "",
        "note": "",
    }
```

- [ ] **Step 2: Add the seen-state helpers**

```python
SEEN_PATH = Path("/data/gnomon-seen.json")


def load_seen() -> dict:
    """Last-seen watched fields per repo. Absent or corrupt reads as empty."""
    try:
        with SEEN_PATH.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_seen(seen: dict) -> None:
    try:
        SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with SEEN_PATH.open("w", encoding="utf-8") as handle:
            json.dump(seen, handle)
    except OSError as err:
        LOG.warning("Could not persist seen-state: %s", err)
```

- [ ] **Step 3: Rewrite `fetch_repo`**

Signature gains `since`, `cut7` and `seen`:

```python
async def fetch_repo(
    session: aiohttp.ClientSession,
    repo: str,
    stale_days: int,
    since: str,
    cut7: str,
    seen: dict,
) -> dict:
    """Build one card from repo metadata, STATE.md and commit activity."""
    card = new_card(repo)

    pushed_at, note = await github.fetch_pushed_at(session, repo)
    if pushed_at:
        card["updated"] = str(pushed_at)[:10]
        card["age"] = state.days_since(pushed_at)
    if note:
        card["note"] = note
        card["state"] = ranking.classify("", "", card["age"], stale_days)
        return card

    payload, activity_note = await github.fetch_commits(session, repo, since)
    if payload is not None:
        card["commits_7d"], card["commits_30d"] = ranking.count_commits(payload, cut7)
        card["momentum"] = ranking.momentum(card["commits_7d"], card["commits_30d"])

    body, state_note = await github.fetch_state_md(session, repo)
    meta: dict = {}
    if body is None:
        card["note"] = state_note
    else:
        parsed, parse_note = state.parse_front_matter(body)
        if parsed is None:
            card["note"] = parse_note
        else:
            meta = parsed

    card["project"] = str(meta.get("project") or card["project"]).strip()
    card["phase"] = state.normalise_phase(meta.get("phase"))
    card["stakes"] = state.normalise_stakes(meta.get("stakes"))
    card["blocker"] = str(meta.get("blocker") or "").strip()

    steps, steps_note = state.parse_steps(meta.get("steps"))
    card["steps"] = steps
    card["steps_total"] = len(steps)
    card["steps_done"] = sum(1 for s in steps if s["state"] == "done")
    card["next"] = state.current_step(steps) or (
        "" if steps else str(meta.get("next") or "").strip()
    )

    target = state.to_date(meta.get("target"))
    if target is not None:
        card["target"] = target.isoformat()
        card["days_to_target"] = state.days_until(target)

    card["state"] = ranking.classify(
        card["blocker"], card["phase"], card["age"], stale_days
    )
    card["debt"] = ranking.debt(
        card["age"], stale_days, card["blocker"], card["days_to_target"]
    )
    card["debt_reason"] = ranking.debt_reason(
        card["age"], stale_days, card["blocker"], card["days_to_target"]
    )
    card["order_reason"], card["order_badge"] = ranking.order_reason(card)

    current = state.watched_values(meta)
    gone = state.vanished(seen.get(repo, {}), current)
    seen[repo] = current

    for candidate in (activity_note, steps_note, state.vanished_note(gone)):
        if candidate and not card["note"]:
            card["note"] = candidate
    if not card["note"] and not card["next"]:
        card["note"] = "No next action set"
    return card
```

- [ ] **Step 4: Rewrite `refresh`**

```python
async def refresh(app: web.Application) -> None:
    """Pull every configured repo and cache the result."""
    options = load_options()
    app["options"] = options

    stale_days = int(options.get("stale_days", 14))
    repos = options.get("repos") or []
    if not repos:
        app["cache"] = {
            "projects": [],
            "fetched": None,
            "stale_days": stale_days,
            "phases": state.PHASES,
            "error": "No repos configured",
        }
        return

    headers = {"User-Agent": "gnomon", "X-GitHub-Api-Version": "2022-11-28"}
    token = options.get("github_token") or ""
    if token:
        headers["Authorization"] = f"Bearer {token}"

    since, cut7 = ranking.commit_cutoffs(datetime.now(timezone.utc))
    seen = load_seen()
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        cards = await asyncio.gather(
            *(
                fetch_repo(session, repo, stale_days, since, cut7, seen)
                for repo in repos
            )
        )
    save_seen(seen)

    ordered = sorted(list(cards), key=ranking.order_key)
    ranking.assign_roles(ordered)
    app["cache"] = {
        "projects": ordered,
        "fetched": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stale_days": stale_days,
        "phases": state.PHASES,
        "error": None,
    }
    LOG.info("Refreshed %d repos", len(ordered))
```

- [ ] **Step 5: Fix the startup cache**

In `main()`, the initial cache references `PHASES`. Change to `state.PHASES` and drop any `score`/`priority` keys.

- [ ] **Step 6: Verify everything parses and nothing references retired names**

Run:
```bash
cd gnomon && python3 -c "import ast; [ast.parse(open(f).read()) for f in ('app.py','state.py','ranking.py','github.py','selftest.py')]; print('all parse')"
grep -n 'compute_score\|score_factors\|sort_cards\|\bband(\|priority' app.py || echo "  no retired references"
```
Expected: `all parse` then `no retired references`

- [ ] **Step 7: Run the tests**

Run: `python3 gnomon/selftest.py`
Expected: every test passes, exit 0.

- [ ] **Step 8: Commit**

```bash
git add gnomon/app.py
git commit -m "Assemble cards from momentum and debt"
```

---

## Task 6: Rewrite the panel

**Files:**
- Modify: `gnomon/www/index.html`

**Interfaces:**
- Consumes: the card shape from Task 5 — `role`, `order_reason`, `order_badge`, `debt_reason`, `commits_7d`, `commits_30d`, `momentum`, plus the unchanged display fields.
- Produces: nothing consumed by later tasks.

The panel is rebuilt with DOM construction rather than HTML strings. Delete these
existing JS functions entirely: `esc` (400), `num` (407), `ageLabel` (411),
`targetLabel` (420), `segments` (430), `why` (445), `details` (455), `render`
(470), `tally` (511). Keep `stamp` (524), `load` (531) and the three event
listeners unchanged.

With every value written through `textContent`, no escaping helper is needed —
a string can never be interpreted as markup.

- [ ] **Step 1: Write the element helpers**

Insert directly after the `ACCENT` map:

```javascript
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null && text !== "") node.textContent = text;
    return node;
  }

  function accent(c) {
    return ACCENT[c.state] || ACCENT.unknown;
  }

  function activityLabel(c) {
    if (c.momentum === null || c.momentum === undefined) return "unknown";
    if (c.commits_7d) return c.commits_7d + "/wk";
    if (c.commits_30d) return c.commits_30d + "/mo";
    return "quiet";
  }

  function cardShell(c, className) {
    var card = el("article", className);
    card.setAttribute("data-state", c.state);
    card.setAttribute("data-repo", c.repo);
    card.style.setProperty("--accent", accent(c));
    if (open[c.repo]) card.classList.add("open");
    return card;
  }

  function metaRow(parts) {
    var row = el("div", "meta");
    parts.filter(Boolean).forEach(function (part, i) {
      if (i) row.appendChild(el("i", null, "\u00b7"));
      row.appendChild(el("span", null, part));
    });
    return row;
  }

  function blockerBlock(c) {
    if (!c.blocker) return null;
    var wrap = el("div", "blocker");
    wrap.appendChild(el("b", null, "BLOCKED"));
    wrap.appendChild(el("span", null, c.blocker));
    return wrap;
  }
```

- [ ] **Step 2: Write the progress and detail builders**

```javascript
  function segments(c) {
    if (!c.steps_total) return null;
    var segs = el("div", "segs");
    c.steps.forEach(function (s) {
      var cls = "seg";
      if (s.state === "done") cls += " done";
      else if (s.state === "current") cls += " current";
      segs.appendChild(el("div", cls));
    });
    return segs;
  }

  function progressRow(c) {
    var segs = segments(c);
    if (!segs) return null;
    var row = el("div", "prog");
    row.appendChild(segs);
    row.appendChild(el("span", "count", c.steps_done + " / " + c.steps_total));
    return row;
  }

  function stepList(c) {
    if (!c.steps || !c.steps.length) return null;
    var list = el("ol");
    c.steps.forEach(function (s) {
      var item = el("li", s.state);
      var mark = s.state === "done" ? "\u2713" : (s.state === "current" ? "\u25cf" : "\u25cb");
      item.appendChild(el("span", "mark", mark));
      item.appendChild(el("span", null, s.text));
      list.appendChild(item);
    });
    return list;
  }

  function detailBlock(c) {
    var steps = stepList(c);
    var reason = c.order_reason
      ? c.order_reason + (c.debt_reason ? " \u00b7 " + c.debt_reason : "")
      : "";
    if (!steps && !reason) return null;
    var wrap = el("div", "steps");
    var inner = el("div", "steps-inner");
    if (steps) inner.appendChild(steps);
    if (reason) inner.appendChild(el("div", "why", reason));
    wrap.appendChild(inner);
    return wrap;
  }

  function addIf(parent, child) {
    if (child) parent.appendChild(child);
  }
```

- [ ] **Step 3: Write the three card builders**

```javascript
  function heroCard(c) {
    var card = cardShell(c, "card hero");
    var row = el("div", "row1");
    row.appendChild(el("span", "project", c.project));
    row.appendChild(el("span", "badge", c.order_badge));
    card.appendChild(row);

    addIf(card, progressRow(c));
    card.appendChild(
      c.next ? el("div", "hero-next", c.next)
             : el("div", "hero-next empty", "Nothing in flight")
    );
    addIf(card, blockerBlock(c));
    card.appendChild(metaRow([c.stakes, c.phase, activityLabel(c)]));
    addIf(card, detailBlock(c));
    return card;
  }

  function rescueCard(c) {
    var card = cardShell(c, "card rescue");
    card.appendChild(el("div", "rescue-tag", "\u25c8 NEEDS RESCUE"));
    var row = el("div", "row1");
    row.appendChild(el("span", "project", c.project));
    row.appendChild(el("span", "age", c.debt_reason));
    card.appendChild(row);
    if (c.next) card.appendChild(el("div", "next", c.next));
    addIf(card, detailBlock(c));
    return card;
  }

  function tailRow(c) {
    var card = cardShell(c, "card tail");
    var row = el("div", "row1");
    row.appendChild(el("span", "project", c.project));
    row.appendChild(el("span", "age", activityLabel(c)));
    row.appendChild(
      el("span", "count", c.steps_total ? c.steps_done + "/" + c.steps_total : "\u2014")
    );
    card.appendChild(row);
    addIf(card, segments(c));
    addIf(card, detailBlock(c));
    return card;
  }
```

- [ ] **Step 4: Write render and tally**

```javascript
  function render(cards) {
    board.textContent = "";
    if (!cards.length) {
      board.appendChild(el("div", "empty-state", "No projects tracked yet."));
      return;
    }
    cards.forEach(function (c) {
      if (c.role === "hero") board.appendChild(heroCard(c));
      else if (c.role === "rescue") board.appendChild(rescueCard(c));
      else board.appendChild(tailRow(c));
    });
  }

  function tally(cards) {
    var active = 0, blocked = 0, stale = 0;
    cards.forEach(function (c) {
      if (c.commits_7d) active++;
      if (c.state === "blocked") blocked++;
      if (c.state === "stale") stale++;
    });
    document.getElementById("t-active").textContent  = active;
    document.getElementById("t-blocked").textContent = blocked;
    document.getElementById("t-stale").textContent   = stale;
    document.getElementById("t-total").textContent   = cards.length;
  }
```

- [ ] **Step 5: Update the stat tile markup**

In the `<div class="tiles">` block, change the first tile's id and label:

```html
    <div class="tile"><b id="t-active">—</b><span>Active</span></div>
    <div class="tile"><b id="t-blocked">—</b><span>Blocked</span></div>
    <div class="tile"><b id="t-stale">—</b><span>Stale</span></div>
    <div class="tile"><b id="t-total">—</b><span>Tracked</span></div>
```

- [ ] **Step 6: Add the hero, rescue and tail styles**

Add after the existing `.card` rules:

```css
.card.hero { padding: 1.1rem 1rem 1rem; margin-bottom: .6rem; }
.card.hero .project { font-size: .875rem; font-weight: 590; color: var(--dim); }
.card.hero .hero-next {
  font-size: 1.3125rem;
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: -.02em;
  margin: .1rem 0;
}
.card.hero .hero-next.empty {
  font-size: 1rem;
  font-weight: 400;
  color: var(--dimmer);
  font-style: italic;
}
.card.hero .prog { margin: .5rem 0 .7rem; }

.badge {
  margin-left: auto;
  flex: none;
  font-family: var(--mono);
  font-size: .5938rem;
  font-weight: 600;
  letter-spacing: .07em;
  color: var(--accent);
  border: 1px solid currentColor;
  border-radius: 980px;
  padding: .1rem .4rem;
}

.card.rescue { margin-bottom: .7rem; }
.rescue-tag {
  font-family: var(--mono);
  font-size: .5625rem;
  font-weight: 600;
  letter-spacing: .09em;
  color: var(--accent);
  margin-bottom: .3rem;
}
.card.rescue .project { font-size: .9375rem; }
.card.rescue .age { margin-left: auto; }
.card.rescue .next { font-size: .875rem; color: var(--dim); margin-top: .2rem; }

.card.tail { padding: .7rem .9rem .6rem; margin-bottom: .35rem; }
.card.tail .project { font-size: .875rem; font-weight: 500; }
.card.tail .age { margin-left: auto; }
.card.tail .count { margin-left: .4rem; }
.card.tail .segs { margin-top: .45rem; }
```

- [ ] **Step 7: Verify the constraints statically**

Run:
```bash
cd /Users/Anthony/Code/gnomon
grep -n 'innerHTML' gnomon/www/index.html && echo "FAIL: innerHTML present" || echo "PASS: no innerHTML"
grep -nE "fetch\(" gnomon/www/index.html
grep -nE "['\"]/api/" gnomon/www/index.html || echo "PASS: no leading slash"
grep -niE 'https?://|cdn|<script src|localStorage|sessionStorage' gnomon/www/index.html || echo "PASS: no external refs"
grep -n 'function esc' gnomon/www/index.html && echo "FAIL: esc should be deleted" || echo "PASS: esc removed"
```
Expected: `PASS: no innerHTML`, one relative `fetch(` line, `PASS: no leading slash`, `PASS: no external refs`, `PASS: esc removed`.

- [ ] **Step 8: Verify the structure under a DOM stub**

Write a throwaway harness OUTSIDE the repo (use the scratch directory, never
commit it). It must implement only what the panel uses: `createElement`,
`appendChild`, `className`, `textContent`, `setAttribute`, `classList.add`,
`style.setProperty`, and `getElementById`. Serialise the resulting tree and
assert:

- exactly one element whose class contains `hero`
- at most one whose class contains `rescue`
- every remaining card is `tail`
- a project named `<img src=x onerror=alert(1)>` is stored as a `textContent`
  string on a node, and appears nowhere as parsed child elements

Expected: 1 hero, 0 or 1 rescue, remainder tail, and the injected name present
only as text.

The last assertion is the XSS gate. With `textContent` it holds structurally
rather than by escaping — which is why `esc` is gone.

- [ ] **Step 9: Commit**

```bash
git add gnomon/www/index.html
git commit -m "Rebuild the panel around a hero and a rescue slot"
```

---

## Task 7: Release 0.4.0

**Files:**
- Modify: `gnomon/config.yaml`, `gnomon/CHANGELOG.md`, `gnomon/DOCS.md`, `STATE.md`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: nothing.

- [ ] **Step 1: Bump the version**

In `gnomon/config.yaml`, line 3: `version: "0.4.0"`

- [ ] **Step 2: Add the changelog entry**

Insert after `# Changelog`:

```markdown
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
```

- [ ] **Step 3: Update DOCS.md**

Replace the "How priority is computed" section with a "How the board is ordered" section covering the two tiers, the momentum formula, debt, and the hero/rescue/tail roles. Replace the worked-examples table with the golden order.

Add to the `blocker` row of the field table, and as its own line under the schema:

> **Waiting on yourself is not a blocker.** A blocker is an external dependency —
> a vendor key, someone else's review, an outage. Your own next action belongs in
> `steps` as the `[>]`. A blocker adds 1.5 to debt and can pull a project into
> the rescue slot, so mislabelling one costs you a real alert.

Update the "Keeping it current" blockquote: freshness comes from commits, not from anything typed.

- [ ] **Step 4: Update this repo's STATE.md**

Mark `[x] Panel redesign for the six-field card` done, and add `[>] Momentum board with hero and rescue`.

- [ ] **Step 5: Verify**

Run:
```bash
cd /Users/Anthony/Code/gnomon
python3 -c "import yaml; [yaml.safe_load(open(f)) for f in ['repository.yaml','gnomon/config.yaml','gnomon/build.yaml']]" && echo "YAML ok"
python3 -c "import sys,yaml; t=open('STATE.md').read(); assert t.startswith('---'); d=yaml.safe_load(t.split('---',2)[1]); s=d.get('steps',[]); assert all(isinstance(x,str) for x in s); cur=[x for x in s if x.startswith('[>]')]; assert len(cur)<=1, cur; print(d['project'], len(s),'steps',sum(1 for x in s if x.startswith('[x]')),'done')"
grep -n 'version:' gnomon/config.yaml
python3 gnomon/selftest.py
```
Expected: `YAML ok`, the STATE.md line, `version: "0.4.0"`, all tests passing.

- [ ] **Step 6: Commit**

```bash
git add gnomon/config.yaml gnomon/CHANGELOG.md gnomon/DOCS.md STATE.md
git commit -m "Gnomon 0.4.0"
```

- [ ] **Step 7: Stop and ask before pushing**

Do not push. Report what changed and wait for explicit permission.

---

## Self-review notes

**Spec coverage.** Momentum formula → Task 2–3. Two-tier ordering → Task 3. Debt marks-not-positions → Task 3. Hero suppression rules including unknown-momentum → Task 3 step 5. Rescue floor, below-fold and parked exclusion → Task 3. `order_reason` table → Task 3 step 9. Field role changes → Task 5. Data model add/remove → Task 5 step 1. Unknown-is-not-zero → Task 2 step 5 and Task 3 momentum. Vanished-field detection → Task 4. Module split and Dockerfile → Task 1. Surface, tiles, edge cases → Task 6. API cost → no code, documented in Task 7. Rollout, blocker guidance → Task 7.

**Known gap, deliberate.** The spec's "everything dormant" edge case (no hero, rescue present, tail dimmed) has no dedicated test. It is the composition of two behaviours already covered — hero suppression and rescue selection — so a third test would assert nothing new.

**Type consistency.** `order_reason` returns a 2-tuple everywhere it appears. `momentum` returns `int | None` and every consumer handles `None`. `assign_roles` mutates and returns `None`; no caller uses a return value. `count_commits` returns `(recent, total)` in that order at both its definition and its call site in Task 5.
