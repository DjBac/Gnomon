"""Ordering: how cards are ranked and why. No network, no aiohttp."""

from __future__ import annotations

import datetime

FRESH_MAX = 6
DEFAULT_STAKES = "personal"
MOMENTUM_RECENT_DAYS = 7
MOMENTUM_WINDOW_DAYS = 30
RECENT_WEIGHT = 3


def classify(blocker: str, phase: str, age: int | None, stale_days: int) -> str:
    if blocker:
        return "blocked"
    if phase == "parked":
        return "parked"
    if age is None:
        return "unknown"
    if age <= FRESH_MAX:
        return "fresh"
    if age <= stale_days:
        return "aging"
    return "stale"


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
